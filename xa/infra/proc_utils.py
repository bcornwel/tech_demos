"""
This file contains process management utilities
Primarily this include the ResourceManager class which is used to manage the thread and process resources
"""


import atexit
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import Future, as_completed
from concurrent.futures._base import RUNNING
from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor
from multiprocessing import Manager
from typing import Callable

from infra.file_utils import get_project_root


def start_profiling(log=False) -> dict:
    """
    Starts function profiling
    #TODO: add timing, probably need to use if event == "return":
    Args:
        log (bool, optional): whether or not to log each function call. Defaults to False.

    Returns:
        dict: the profiling dictionary containing the functions and times called
    """
    root_path = get_project_root(as_str=True)
    root_len = len(root_path)
    profiling_dict = {}

    def trace_calls(frame, event, arg):
        if event != "call":
            return
        co = frame.f_code
        func_filename = co.co_filename
        if not func_filename.startswith(root_path):
            return
        func_name = co.co_name
        caller = frame.f_back
        func_id = f"{func_filename[root_len:]}:{func_name}"
        profiling_dict.setdefault(func_id, 1)
        profiling_dict[func_id] += 1
        if log:
            print(f"Call #{profiling_dict[func_id]} to {func_name} on line {frame.f_lineno} of {func_filename} from line {caller.f_lineno} of {caller.f_code.co_filename}")

    import sys
    sys.setprofile(trace_calls)
    return profiling_dict


def set_exit_handler(profiling=False):
    """
    sets up the exit handler

    Args:
        profiling (bool, optional): whether or not to set up profiling. Defaults to False.
    """
    if profiling:
        profiling_dict = start_profiling(log=False)

    def exit_handler():
        if profiling:
            for k,v in sorted(profiling_dict.items(), key=lambda item:item[1]):
                print(f"{k}: {v}")
        print("Goodbye")

    import atexit
    atexit.register(exit_handler)


class ThreadExecutor(ThreadPoolExecutor):
    """
    Custom threadpoolexecutor class that has a little more control of threads and better shutdown
    """
    def __init__(self, *args, **kwargs):
        self.log = None
        super().__init__(*args, **kwargs)
        self.futures = dict()

    def submit(self, func: Callable, *args, id=0, **kwargs) -> Future:
        """
        submit a function for thread execution

        Args:
            func (Callable): the function
            id (int): the identifier of the thread

        Returns:
            Future: the pending future object
        """
        future = super().submit(func, *args, **kwargs)
        self.futures[id] = future
        return future
    
    def shutdown(self, wait: bool, cancel_futures: bool):
        """
        shutdown the executor

        Args:
            wait (bool): whether or not to wait for threads
            cancel_futures (bool): whether or not to cancel pending threads

        Returns:
            bool: whether or not shutdown went smoothly
        """
        success = True
        for future in as_completed(self.futures.values(), 5):
            exception = future.exception(1)
            if exception is not None:
                if self.log:
                    self.log.exception(f"Exception stopping thread: {exception}")
            else:
                if self.log:
                    self.log.debug(f"Thread returned '{future.result()}'")
        for sub_thread in self._threads:
            try:
                success = success and sub_thread.cancel() and not sub_thread._state == RUNNING
            except:
                success = False
        try:
            if sys.version_info.minor >= 9:
                super().shutdown(wait=wait, cancel_futures=cancel_futures)
            else:
                super().shutdown(wait=wait)
        except:
            success = False
        return success


class ProcessExecutor(ProcessPoolExecutor):
    """
    Custom processpoolexecutor class that has a little more control of processes and better shutdown
    """
    def __init__(self, *args, **kwargs):
        self.log = None
        super().__init__(*args, **kwargs)
        self.futures = dict()
    
    def submit(self, func: Callable, *args, id=0, **kwargs) -> Future:
        """
        submit a function for process execution

        Args:
            func (Callable): the function
            id (int): the identifier of the process

        Returns:
            Future: the pending future object
        """
        future = super().submit(func, *args, **kwargs)
        self.futures[id] = future
        return future

    def shutdown(self, wait: bool, cancel_futures: bool):
        """
        shutdown the executor

        Args:
            wait (bool): whether or not to wait for processes
            cancel_futures (bool): whether or not to cancel pending processes

        Returns:
            bool: whether or not shutdown went smoothly
        """
        success = True
        for future in as_completed(self.futures.values(), 5):
            exception = future.exception(1)
            if exception is not None:
                if self.log:
                    self.log.exception(f"Exception stopping process: {exception}")
            else:
                if self.log:
                    self.log.debug(f"Process returned '{future.result()}'")
        for sub_process in self._processes.values():
            try:
                success = success and sub_process.kill() and not sub_process._state == RUNNING
            except Exception as e:
                success = False
        try:
            if sys.version_info.minor >= 9:
                super().shutdown(wait=wait, cancel_futures=cancel_futures)
            else:
                super().shutdown(wait=True)
        except:
            success = False
        return success


def _runner(func, id, *args, **kwargs):
    ResourceManager.pids[id] = os.getpid()
    return func(*args, **kwargs)


class ResourceManager:
    """
    Class to manage system resources
    For now, this just contains thread and process pool executors
    planned future support includes
        - analyzing system resources/capabilities
        - intelligently managing threads/processes
    """
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ResourceManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        self.running = True
        self.thread_executor = ThreadExecutor()
        self.process_executor = ProcessExecutor()
        atexit.register(self.shutdown)
        self.log = None
        self.pending:dict = dict()
        self._manager = None
        self.pids:dict = None
    
    def _start(self):
        """
        Starts the manager
        """
        self._manager = Manager()
        self.pids = self._manager.dict()
    
    def _assign_logger(self, log):
        """
        assigns a log object to the resource manager and sub executors

        Args:
            log (Logger): the log obtained by get_log()
        """
        self.log = self.log or log
        self.thread_executor.log = self.log
        self.process_executor.log = self.log

    def submit(self, submission:Callable, *args, thread:bool=True, id=0, **kwargs) -> Future:
        """
        submit a function for a new thread or process if thread=False

        Args:
            submission (Callable): the function to submit for parallelization
            thread (bool, optional): whether to use a thread instead of a process. Defaults to True.
            id (int): the identifier of the process or thread

        Raises:
            Exception: error submitting the job

        Returns:
            Future: the future containing the job, meant for tracking and later result checking
        """
        try:
            if not self._manager:
                self._start()
            if id in self.pending:
                raise Exception(f"{'thread' if thread else 'process'} id {id} already exists in pending jobs. Please change the id in the submission")
            if thread:
                future = self.thread_executor.submit(_runner, submission, id, *args, id=id, **kwargs)
                future.executor = self.thread_executor
            else:
                future = self.process_executor.submit(_runner, submission, id, *args, id=id, **kwargs)
                future.executor = self.process_executor
            future.id = id
            self.pending[id] = future
            return future
        except Exception as submission_exception:
            raise Exception(f"Unable to submit {submission.__name__}: '{submission_exception}'")

    def get_results_from_futures(self, futures) -> dict:
        results = {}
        for future in as_completed(futures):
            results[future.id] = future.result()
            self.pending.pop(future.id).executor.futures.pop(future.id)  # this is probably a terrible way to do this
        return results
    
    def get_results_from_ids(self, ids) -> dict:
        results = {}
        futures = [f for f in self.pending if f.id in ids]
        for future in as_completed(futures):
            results[future.id] = future.result()
            self.pending.pop(future.id).executor.futures.pop(future.id)  # this is probably a terrible way to do this
        return results

    def kill_process(self, id):
        if id not in self.pending:
            raise Exception("Unable to kill a process that is not registered")
        if id not in self.pids:
            raise Exception("Unable to kill a process ID that is not registered")
        # assert subprocess.check_call(f"kill -9 {self.pids[id]}".split(' ')), f"killing process {self.pids[id]} failed. You may not have permissions. Try killing it manually in sudo mode"
        try:
            os.kill(self.pids[id], signal.SIGKILL)
            time.sleep(.1)
            os.kill(self.pids[id], 0)  # send a noop signal to check if it still exists
        except OSError as o:  # does not exist anymore
            try:
                self.pending.pop(id).executor.futures.pop(id)
            except:  # shouldn't fail, but we don't care if it doesn't exist at this point
                pass
            self.pids.pop(id)
        except Exception as e:
            if "no such process" in f"{e}".lower():
                try:
                    self.pending.pop(id).executor.futures.pop(id)
                except:  # shouldn't fail, but we don't care if it doesn't exist at this point
                    pass
                self.pids.pop(id)
            else:
                raise Exception(f"Killing process {self.pids[id]} failed: {e}")
        else:
            raise Exception(f"Killing process {self.pids[id]} failed. You may not have permissions. Try killing it manually in sudo mode")
        
    def kill_processes(self, ids, permissive=False) -> int:
        failures = 0
        for id in ids:
            if permissive:
                try:
                    self.kill_process(id)
                except:
                    failures += 1
            else:
                self.kill_process(id)
        return failures

    def get_max_id(self):
        if len(self.pending.keys()):
            return max(self.pending.keys())
        return 0

    def shutdown(self, wait:bool=False, cancel_futures:bool=True):
        """
        close out any threads/processes running

        Args:
            wait (bool, optional): whether or not to wait for in progress threads/processes. Defaults to False.
            cancel_futures (bool, optional): whether or not to cancel pending threads/processes. Defaults to True.
        """
        if not self.running:
            return
        self.running = False
        self.thread_executor.shutdown(wait, cancel_futures)
        self.process_executor.shutdown(wait, cancel_futures)


ResourceManager = ResourceManager()


def run_command(cmd:str, shell=False, output=True, log=None, label=""):
    """
    Run a command using Popen as if in the command line. Used to call hl-smi, hccl_al, etc

    Args:
        cmd (str): the command to run
        shell (bool): whether to run in shell mode or not
        output (bool): whether to let the output go to the console or not

    Returns:
        tuple(list, list, int): list of stdout lines, list of stderr lines, and the return code
    """
    if not log:
        log = ResourceManager.log
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split(' ')
        elif isinstance(cmd, list) and shell:
            cmd = ' '.join(cmd)
        if (isinstance(cmd, str) and shell) or (isinstance(cmd, list) and not shell):
            pass  # best case scenario
        else:
            raise Exception(f"Cmd '{cmd}' is the wrong format, it should be a string for shell calls or list of strings for non-shell calls")
        if len(f"{label}"):
            out_label = f"Proc {label}: "
            label_str = f" with stdout/stderr label '{out_label}'"
        else:
            out_label = label_str = ""
        shell_str = " in shell mode" if shell else ""
        cmd_friendly = ' '.join(cmd) if isinstance(cmd, list) else cmd
        log.debug(f"Running command line: '{cmd_friendly}'{shell_str}{label_str}")
        stdout = []
        stderr = []
        if shell:
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in p.stdout:
            line = line.decode().strip()
            if output:
                log.stdout(f"{out_label}{line}")
            stdout.append(f"{out_label}{line}")

        for line in p.stderr:
            line = line.decode().strip()
            if output:
                log.stderr(f"{out_label}{line}")
            stdout.append(f"{out_label}{line}")
        p.wait()
        return stdout, stderr, p.returncode
    except Exception as e:
        log.error(f"Error running command '{cmd}': {e}")
        raise Exception(e)
