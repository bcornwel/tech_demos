"""
This file demonstrates the performance differences between serial, threaded, and multiprocessing tasks
There are two main test types, factorization, and file reading.
I copied the majority of the factorization code from https://eli.thegreenplace.net/2012/01/16/python-parallelizing-cpu-bound-tasks-with-multiprocessing/
"""
import time, random, math, threading, multiprocessing


def factorize_naive(n):
    """
    A naive factorization method. Take integer 'n', return list of
    factors.
    """
    if n < 2:
        return []
    factors = []
    p = 2

    while True:
        if n == 1:
            return factors

        r = n % p
        if r == 0:
            factors.append(p)
            n = n / p
        elif p * p >= n:
            factors.append(n)
            return factors
        elif p > 2:
            # Advance in steps of 2 over odd numbers
            p += 2
        else:
            # If p == 2, get to 3
            p += 1
    assert False, "unreachable"

def serial_factorizer(nums):
    return {n: factorize_naive(n) for n in nums}

def th_factorization_worker(nums, outdict):
    """ 
    The worker function, invoked in a thread. 'nums' is a
    list of numbers to factor. The results are placed in
    outdict.
    """
    for n in nums:
        outdict[n] = factorize_naive(n)

def threaded_factorizer(nums, nthreads):
    # Each thread will get 'chunksize' nums and its own output dict
    chunksize = int(math.ceil(len(nums) / float(nthreads)))
    threads = []
    outs = [{} for i in range(nthreads)]

    for i in range(nthreads):
        # Create each thread, passing it its chunk of numbers to factor
        # and output dict.
        t = threading.Thread(
                target=th_factorization_worker,
                args=(nums[chunksize * i:chunksize * (i + 1)],
                      outs[i]))
        threads.append(t)
        t.start()

    # Wait for all threads to finish
    for t in threads:
        t.join()

    # Merge all partial output dicts into a single dict and return it
    return {k: v for out_d in outs for k, v in out_d.items()}

def mp_factorization_worker(nums, out_q):
    """
    The worker function, invoked in a process. 'nums' is a
    list of numbers to factor. The results are placed in
    a dictionary that's pushed to a queue.
    """
    outdict = {}
    for n in nums:
        outdict[n] = factorize_naive(n)
    out_q.put(outdict)

def mp_factorizer(nums, nprocs):
    # Each process will get 'chunksize' nums and a queue to put his out
    # dict into
    out_q = multiprocessing.Queue()
    chunksize = int(math.ceil(len(nums) / float(nprocs)))
    procs = []

    for i in range(nprocs):
        p = multiprocessing.Process(
                target=mp_factorization_worker,
                args=(nums[chunksize * i:chunksize * (i + 1)], out_q))
        p.start()
        procs.append(p)

    
    # Collect all results into a single result dict. We know how many dicts
    # with results to expect.
    resultdict = {}
    for i in range(nprocs):
        resultdict.update(out_q.get())

    # Wait for all worker processes to finish
    for p in procs:
        p.join()

    return resultdict

def file_writer(length, file_name):
    s = "This is a test sentence\n"
    with open(file_name, 'w') as fp:
        for i in range(length):
            fp.write(s)
    return len(s)*length

def factorization_test():
    length = 250_000
    # data = range(length)
    data = list(range(length))
    random.shuffle(data)

    s_start = time.perf_counter()
    serial_factorizer(data)
    s_end = time.perf_counter()
    print(f"Serial Factorization: {s_end-s_start}")

    t_start = time.perf_counter()
    threaded_factorizer(data, 2)
    t_end = time.perf_counter()
    print(f"Threading Factorization 2x: {t_end-t_start}")

    t_start = time.perf_counter()
    threaded_factorizer(data, 4)
    t_end = time.perf_counter()
    print(f"Threading Factorization 4x: {t_end-t_start}")

    t_start = time.perf_counter()
    threaded_factorizer(data, 8)
    t_end = time.perf_counter()
    print(f"Threading Factorization 8x: {t_end-t_start}")

    m_start = time.perf_counter()
    mp_factorizer(data, 2)
    m_end = time.perf_counter()
    print(f"Multiprocessing Factorization 2x: {m_end-m_start}")

    m_start = time.perf_counter()
    mp_factorizer(data, 4)
    m_end = time.perf_counter()
    print(f"Multiprocessing Factorization 4x: {m_end-m_start}")

    m_start = time.perf_counter()
    mp_factorizer(data, 8)
    m_end = time.perf_counter()
    print(f"Multiprocessing Factorization 8x: {m_end-m_start}")

def read_io(f, n):
    sum_chars = 0
    for i in range(n):
        with open(f, 'r') as fp:
            sum_chars += len(fp.readlines())
    return sum_chars

def th_read_worker(f, i, num, outdict):
    outdict[i] = read_io(f, num)


def threaded_reader(f, num, nthreads):
    chunksize = int(num / nthreads)
    extra = num % nthreads
    threads = []
    outs = [{} for i in range(nthreads)]

    for i in range(nthreads):
        count = chunksize + extra if i == 0 else chunksize
        t = threading.Thread(
                target=th_read_worker,
                args=(f, i, count, outs[i]))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return sum(list(outd.values())[0] for outd in outs)

def mp_read_worker(f, i, num, out_q):
    outdict = {i: read_io(f, num)}
    out_q.put(outdict)

def mp_reader(f, num, nprocs):
    out_q = multiprocessing.Queue()
    chunksize = int(num / nprocs)
    extra = num % nprocs
    procs = []

    for i in range(nprocs):
        count = chunksize + extra if i == 0 else chunksize
        p = multiprocessing.Process(
                target=mp_read_worker,
                args=(f, i, count, out_q))
        p.start()
        procs.append(p)

    resultdict = {}
    for i in range(nprocs):
        resultdict.update(out_q.get())

    for p in procs:
        p.join()

    return sum(out for out in resultdict.values())

def file_io_test():
    times = 1000
    lines = 100000
    f_name = "test_file.txt"
    print(f"Wrote {file_writer(lines, f_name)} chars to {f_name} with {lines} lines")

    s_start = time.perf_counter()
    print(read_io(f_name, times))
    s_end = time.perf_counter()
    print(f"Serial Read: {s_end-s_start}")

    t_start = time.perf_counter()
    print(threaded_reader(f_name, times, 2))
    t_end = time.perf_counter()
    print(f"Threaded Read 2x: {t_end-t_start}")

    t_start = time.perf_counter()
    print(threaded_reader(f_name, times, 4))
    t_end = time.perf_counter()
    print(f"Threaded Read 4x: {t_end-t_start}")

    t_start = time.perf_counter()
    print(threaded_reader(f_name, times, 8))
    t_end = time.perf_counter()
    print(f"Threaded Read 8x: {t_end-t_start}")

    m_start = time.perf_counter()
    print(mp_reader(f_name, times, 2))
    m_end = time.perf_counter()
    print(f"Multiprocessing Read 2x: {m_end-m_start}")

    m_start = time.perf_counter()
    print(mp_reader(f_name, times, 4))
    m_end = time.perf_counter()
    print(f"Multiprocessing Read 4x: {m_end-m_start}")

    m_start = time.perf_counter()
    print(mp_reader(f_name, times, 8))
    m_end = time.perf_counter()
    print(f"Multiprocessing Read 8x: {m_end-m_start}")


if __name__ == "__main__":
    # factorization_test()

    file_io_test()
