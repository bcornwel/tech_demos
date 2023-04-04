"""
This file demonstrates the ability to capture output of driver code that is sent to stderr, as well as handling for segfaults
"""

import datetime
from io import TextIOWrapper
import subprocess


class UnbufferedStream:
    """
    Object used to flush a stream automatically.
    Used to expedite stream filtering
    """
    def __init__(self, stream):
        self.stream:TextIOWrapper = stream

    def write(self, data):
        """
        print statement

        Args:
            data (Any): data to write
        """
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, datas):
        """
        multi-line print statement

        Args:
            datas (Any): data to write
        """
        self.stream.writelines(datas)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


class InternalData:
    def __init__(self, data="Some internal data") -> None:
        self.data = data
    
    def do_ll_cmd(self, data):
        print(f"Doing LL cmd: {data}")
    
    def do_ll_kw_cmd(self, kw1="test"):
        print(f"Doing kw cmd: '{kw1}'")


class API:
    def __init__(self, data=None):
        self.reload(data)
    
    def reload(self, data):
        print("Reloading API")
        self.data = InternalData(data)
    
    def do_hl_cmd(self, data):
        print(f"Doing HL cmd: {data}")

    def handle_input(self, data):
        pieces = data.split(',')
        cmd = pieces[0]
        args = []
        kwargs = dict()
        for piece in pieces[1:]:
            if '=' in piece:
                key, value = piece.split('=')
                kwargs[key.strip()] = value.strip()
            else:
                args.append(piece.strip())
        try:
            func = getattr(self.data, cmd)
        except:
            func = getattr(self, cmd)
        func(*args, **kwargs)

class APIRunner:
    def __init__(self) -> None:
        self.process = subprocess.Popen("python -m api".split(' '), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ready = False
        while self.process.poll() is None and not ready:
            out = self.process.stdout.readline().decode()
            print("Received:", out)
            ready = "Waiting for command" in out

    def __getattr__(self, item):
        attribute = self.__dict__.get(item, None)
        if not attribute:
            # @functools.wraps(func)
            def wrapper(*args, **kwargs):
                c_timeout = kwargs.get("c_timeout", 10)
                kws = ', '.join(f"{k}={v}" for k, v in kwargs.items())
                return self.run_command(item + ', ' + ', '.join(args) + (', ' + kws if len(kws) else ''), c_timeout=c_timeout)
            return wrapper
        return attribute

    def run_command(self, cmd, c_timeout=10):
        print(f"Running {cmd}")
        done = False
        self.process.stdin.write(f"{cmd}\n".encode())
        self.process.stdin.flush()
        start = datetime.datetime.now()
        end_time = start + datetime.timedelta(seconds=c_timeout)
        print("looping")
        while not done and (datetime.datetime.now() < end_time):
            out = self.process.stdout.readline().decode()
            print(f"out: {out}")
            if "API EOF" in out:
                done = True
        print("finished running command")


def run_interactive_api(data):
    sys.stdout = UnbufferedStream(sys.stdout)
    sys.stderr = UnbufferedStream(sys.stderr)
    print(f"Starting interactive with '{data}'")
    api = API(data)
    should_run = True
    while should_run:
        try:
            cmd = input("Waiting for command\n").replace('\r', '').replace('\n', '')
            if cmd == "stop":
                should_run = False
                print("stopping")
            else:
                print(f"Cmd to run: '{cmd}'")
                api.handle_input(cmd)
        except Exception as e:
            print(f"oops: {e}")
        print("API EOF")


if __name__ == "__main__":
    import sys
    run_interactive_api(f"{sys.argv[1:]}")
