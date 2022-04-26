"""
This file demonstrates multiprocess distributed workers communicating with inter-process queues
There is a management process that gives tasks out to workes when they don't have tasks to fulfill
There is a centralized logger object which gets pickled to each process and can print/store messages from any process
There is a central state object which allows control over all of the processes (as long as they pay attention to the state)
Messages passed are either strings requesting more work, or tasks which are classes with a standard call function.
This could be abstracted into Task/Event classes that have more information and allow for job tracking, as well as different modes of handling
"""

import multiprocessing
import time
import queue
import random

global_timeout = 20


class StateDef:
    Starting = "starting"
    Running = "running"
    Stop = "stop"
    Stopping = "stopping"
    Dead = "dead"


class StateManager:
    def __init__(self):
        self.start()

    def start(self):
        self.state = StateDef.Starting

    def run(self):
        self.state = StateDef.Running

    def stopping(self):
        self.state = StateDef.Stopping

    def stop(self):
        self.state = StateDef.Stop

    def dead(self):
        self.state = StateDef.Dead

    def is_stopped(self):
        return self.state == StateDef.Stop

    def is_dead(self):
        return self.state == StateDef.Dead

    def should_run(self):
        return not self.state == StateDef.Stop and not self.state == StateDef.Stopping

    def should_cleanup(self):
        return self.state == StateDef.Stopping


class CentralizedLogger:
    def __init__(self, global_state):
        self.log = multiprocessing.Queue()
        self.global_state = global_state

    def print(self, msg):
        print(msg)
        self.log.put(msg)

    def dump(self):
        out = []
        try:
            while not self.global_state.is_stopped():
                out.append(self.log.get(False))
        except queue.Empty as e:
            pass
        return out


class EventClass(object):
    def __init__(self, name):
        self.name = name
    
    def do_something(self, log):
        try:
            log.print(f'Doing {self.name} in {multiprocessing.current_process().name}!')
        except Exception as do_exc:
            log.print(f"woops: {do_exc}")


def work_process(s, l, q, o=None):
    print("Worker starting")
    timeout = global_timeout
    while timeout and s.should_run():
        try:
            if not q.empty():
                obj = q.get()
                if isinstance(obj, str):
                    l.print(obj)
                else:
                    obj.do_something(l)
            else:
                if not timeout%5:  # 5 runs in a row will show nothing to do
                    l.print("Worker has nothing to do")
                    if o:
                        o.put(f"{multiprocessing.current_process().name} is bored")

        except Exception as work_exc:
            l.print(f"oh no: {work_exc}")
        timeout -= 1
        time.sleep(0.5)

def management_process(s, l, q, o1, o2):
    print("Manager starting")
    timeout = global_timeout
    while timeout and s.should_run():
        try:
            if not q.empty():
                obj = q.get()
                if "bored" in obj:
                    if "Process-1" in obj:
                        o1.put(EventClass(f'task {random.random()}'))
                    elif "Process-2" in obj:
                        o2.put(EventClass(f'task {random.random()}'))
                    else:
                        l.print("Unexpected worker!")
                else:
                    l.print("Unexpected message!")
            else:
                if not timeout%5:  # 5 runs in a row will show nothing to do
                    l.print("Manager has nothing to do")

        except Exception as work_exc:
            l.print(f"oh no: {work_exc}")
        timeout -= 1
        time.sleep(0.5)


if __name__ == "__main__":
    print("Setting up")
    state = StateManager()

    log = CentralizedLogger(state)

    out_queue = multiprocessing.Queue()
    in_queue1 = multiprocessing.Queue()
    in_queue2 = multiprocessing.Queue()
    print("Adding starting tasks to the queues")
    for i in range(0, 10):
        in_queue1.put(EventClass(f'task {i}'))
    for i in range(0, 10):
        in_queue2.put(EventClass(f'task {i}'))

    print("Starting up processors")
    p1 = multiprocessing.Process(target=work_process, args=(state, log, in_queue1, out_queue,))  # worker 1
    p2 = multiprocessing.Process(target=work_process, args=(state, log, in_queue2, out_queue,))  # worker 2
    p3 = multiprocessing.Process(target=management_process, args=(state, log, out_queue, in_queue1, in_queue2))  # manager
    try:
        p1.start()
    except Exception as p1_start_exc:
        print(f"oops1: {p1_start_exc}")
    try:
        p2.start()
    except Exception as p2_start_exc:
        print(f"oops2: {p2_start_exc}")
    try:
        p3.start()
    except Exception as p3_start_exc:
        print(f"oops3: {p3_start_exc}")

    state.run()

    print("putting extra tasks in the queue")
    in_queue1.put(EventClass('task new-1'))
    in_queue2.put(EventClass('task new-2'))

    print("Waiting to stop")
    time.sleep(10)
    state.stopping()
    print("Stopping")
    # Wait for the worker to finish
    in_queue1.close()
    in_queue2.close()
    out_queue.close()
    print("joining queues")
    in_queue1.join_thread()
    in_queue2.join_thread()
    out_queue.join_thread()
    print("joining p1")
    p1.join()
    print("joining p2")
    p2.join()
    print("joining p3")
    p3.join()
    print("dump:", log.dump())
    state.stop()