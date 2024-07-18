import atexit
import collections
from concurrent.futures import as_completed, Future, ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures._base import RUNNING
import datetime
import inspect
import json
import jsonschema
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path, PurePosixPath
import re
import sys
from types import ModuleType
from typing import Callable, Tuple


_ExcInfoType = TypeAlias = None or bool or BaseException


class Const:
    """
    Container for constant strings to be used throughout the code
    """
    ErrorLogName = "errors.log"
    SummaryLogPostfix = "_summary.log"

    LoopBackIP = "127.0.0.1"
    HttpProxy = "http://proxy-dmz.intel.com:911"
    HttpsProxy = "http://proxy-dmz.intel.com:912"

    TestMode = "TEST_MODE"

    class Directories:
        Configs = "configs"  # where config files are generally stored
        Docs = "docs"  # where documentation is stored
        Schemas = "schemas"  # where schemas are stored
        Test = "_test"  # where test files are stored
        VirtualEnv = "env"  # folder for virtual environment data

    class Timeouts:
        """
        Default timeout values
        """
        Response = 15


class RegexStrings:
    """
    Contains useful regex strings
    all regex string unless one-off tests should be located here
    """
    Alpha = r"[a-zA-Z]+"
    AlphaNumeric = r"[a-zA-Z\.0-9]+"
    AlphaNumericWithSpace = r"[a-zA-Z\.0-9 ]+"
    BlockDelete = r"(?i)Delete from"
    BlockDrop = r"(?i)Drop (index|constraint|table|column|primary|foreign|check|database|view)"
    BlockSqlComment = r"--"
    Directory = r"([a-zA-Z]:\\\\)|(\/|\\|\\\\){0,1}(\w+(\/|\\|\\\\))*\w+(\/|\\|\\\\)*"
    Job_ID = r"(\d{6})_(\d)_(\d)_(\d)_(\d{20})"
    Numeric = r"(0-9)+\.*(0-9)+"
    PathLike = r"((?:[^;]*/)*)(.*)"
    PathTraversal = r"(/|\\|\\\\)\.\.(/|\\|\\\\)"
    PythonFile = r"([a-zA-Z]:){0,1}(/|\\|\\\\){0,1}(\w+(/|\\|\\\\))*\w+\.py"
    SessionDir = r"([a-zA-Z]:){0,1}(/|\\|\\\\){0,1}(\w+(/|\\|\\\\))*session_\d{6}_\d{20}"
    Session_ID = r"\d{6}_\d{20}"
    Tuple = r"[a-zA-Z0-9_\(\)\,]"
    Url = r"http(s){0,1}:\/\/(((([0-1]*[0-9]*[0-9]\.|2[0-5][0-5]\.){3})([0-1]*[0-9]*[0-9]|2[0-5][0-5])(:[0-9]{0,4}|[0-5][0-9]{4}|6[0-5][0-5][0-3][0-5])*)|((\d*[a-zA-Z][a-zA-Z0-9\.]*(\-*))+\.[a-zA-Z0-9]{1,3}))((/[\w\-\.]*)*(\?\w+=\w+)*)*"
    MarkdownLink = r"\[.*\]\(.*\)"
    Variable = r"[\w\. ]+"


def get_project_root(as_str=False) -> Path:
    """
    returns the root of the project by getting this file (located in root/) and then going one directory up

    Args:
        as_str (bool, optional): whether or not to return the path as a string instead of a path object. Defaults to False.

    Returns:
        Path: the path to the root of the project
    """
    root = os.path.dirname(os.path.abspath(__file__))
    return root if as_str else Path(root).resolve()


def safe_path(path: str | Path, relative:bool=True) -> Path:
    """
    Converts a path from a string

    Args:
        path (str or Path): a path string
        relative (bool): whether or not to shorten the path to the directory

    Returns:
        Path: a valid path
    """
    str_path = f"{path}" if isinstance(path, Path) else path
    path: Path = path if isinstance(path, Path) else Path(path)
    assert not re.search(RegexStrings.PathTraversal, str_path), "Path traversal detected! Cannot resolve path"
    assert re.fullmatch(RegexStrings.PathLike, str_path), "Path does not match path format! Cannot resolve path"
    path = path.resolve()
    if relative:
        try:
            return path.relative_to(get_project_root().resolve())
        except ValueError:  # not relative to root dir
            return path
    else:
        return path


def import_module_from_path(mod_path:str | Path, relative=False) -> ModuleType:
    """
    Loads a module from a path

    Args:
        mod_path (str or Path): path to the expected module
        relative (bool, optional): whether or not to import the module relative to the root directory (safer). Defaults to True.

    Returns:
        ModuleType: the actual imported module
    """
    import importlib.util
    mod_path: Path = safe_path(mod_path)
    if mod_path.suffix == ".py":
        mod_name = mod_path.stem
        if relative:
            mod_path = mod_path.relative_to(get_project_root())
        mod_path: str = f"{mod_path}"
        assert os.path.exists(mod_path), f"{mod_path} doesn't exist. Can't import it!"
        spec = importlib.util.spec_from_file_location(mod_name, mod_path)
        new_mod = importlib.util.module_from_spec(spec)
        if mod_name != "__main__":  # this will execute the main section instead of just an import
            spec.loader.exec_module(new_mod)
    else:
        from importlib import import_module
        mod_path: str = f"{mod_path}"
        new_mod = import_module(mod_path)
    return new_mod


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


def timedelta_string_to_timedelta(td_str:str) -> datetime.timedelta:
    """
    converts a string that describes a time delta to an actual time delta object

    Args:
        td_str (str): the time delta string

    Returns:
        datetime.timedelta: the time delta
    """
    td_str = td_str.strip('"')
    if "days" in td_str:
        days, delta = td_str.split(" days, ")
        day_delta = datetime.timedelta(days=int(days))
    else:
        delta = td_str
        day_delta = datetime.timedelta()  # no day offset
    if '.' in delta:
        timestamp = datetime.datetime.strptime(delta, "%H:%M:%S.%f")
    else:
        timestamp = datetime.datetime.strptime(delta, "%H:%M:%S")
    delta = datetime.timedelta(days=day_delta.days, hours=timestamp.hour,
                               minutes=timestamp.minute, seconds=timestamp.second)
    return delta


def time_string_to_datetime(time_str:str) -> datetime.datetime:
    """
    converts a string defining a time to an actual datetime object

    Args:
        time_str (str): the time string

    Returns:
        datetime.datetime: the datetime object
    """
    time_str = time_str.strip('"')
    dtime = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
    return dtime


def datetime_to_time_string(date:datetime.datetime, path_mode:bool=False, omit_milliseconds:bool=False) -> str:
    """
    Gets a time string from a datetime object

    Args:
        date (datetime): datetime object
        path_mode (bool, optional): whether or not to make the string path-safe. Defaults to False.
        omit_milliseconds (bool, optional): whether or not to remove milliseconds from string. Defaults to False.

    Returns:
        str: time string
    """
    if not path_mode:
        formatting = f"%Y-%m-%d %H:%M:%S{'.%f' if not omit_milliseconds else ''}"
    else:
        formatting = f"%Y%m%d_%H%M%S{'%f' if not omit_milliseconds else ''}"
    return datetime.datetime.strftime(date, formatting)


def get_friendly_elapsed_time(elapsed) -> str:
    """
    returns a string like
        '1 hour ago'
        '1 day, 2 hours ago'
        '2 hours, 5 minutes ago'
        'now'

    Args:
        elapsed (datetime): the datetime object

    Returns:
        str: the time string in a friendly format
    """
    elapsed_minutes = elapsed.seconds // 60 % 60
    elapsed_hours = elapsed.seconds // 3600
    if not elapsed.days > 0 and not elapsed_hours > 0 and not elapsed_minutes > 0:
        return "now"
    elapsed_minute_str = f"{elapsed_minutes} minute{'s' if elapsed_minutes > 1 else ''}" if elapsed_minutes > 0 else ""
    elapsed_hour_str = f"{elapsed_hours} hour{'s' if elapsed_hours > 1 else ''}" if elapsed_hours > 0 else ""
    elapsed_day_str = f"{elapsed.days} day{'s' if elapsed.days > 1 else ''}" if elapsed.days > 0 else ""

    time_str = f"{elapsed_day_str}"
    time_str += f"{', ' if elapsed.days > 0 and (elapsed_hours > 0 or elapsed_minutes > 0) else ''}"
    time_str += f"{elapsed_hour_str}"
    time_str += f"{', ' if elapsed_hours > 0 and elapsed_minutes > 0 else ''}"
    time_str += f"{elapsed_minute_str}"
    time_str += " ago"
    return time_str


def get_current_time_string() -> str:
    """
    Gets the current time as a string

    Returns:
        str: the time string
    """
    return datetime_to_time_string(datetime.datetime.now())


def get_current_time_string_path_friendly() -> str:
    """
    Gets the current time as a string, but path-safe

    Returns:
        str: the time string
    """
    return datetime_to_time_string(datetime.datetime.now(), path_mode=True, omit_milliseconds=True)


def get_caller_name(layers:int=1):
    """
    Gets the function (and object if possible) that called this function at the nth layer
    e.g. calling get_caller_name(0) would return get_caller_name
         calling get_caller_name(1) would return the function that called get_caller_name

    Args:
        layers (int, optional): How many layers up to check. Defaults to 0.

    Returns:
        str: The caller name string
    """
    func_name = f"{inspect.stack()[layers][3]}"
    try:
        stack = inspect.stack()[layers+1]
    except:
        pass
    try:
        # this line uses reflection to get the name of the class that calls this line
        calling_object = str(stack[0].f_locals["self"].__class__.__name__)
        # this line uses reflection to get the name of the function inside the class that calls this line
        object_function = str(stack[3])
        # this line uses reflection to get the name of the function that calls this log line
        return f"{func_name} in {calling_object}.{object_function}"
    except Exception as class_exception:  # failed to get the class name that called this method. oh well
        return f"Running {func_name}"


def GetLogFormatter(standard=True) -> logging.Formatter:
    """
    Creates a logging.Formatter instance with log line decorations

    Args:
        standard (bool, optional): whether to use the standard format or the simple version. Defaults to True.

    Returns:
        logging.Formatter: The formatter to apply to a logging.Logger instance
    """
    class StandardFormatter(logging.Formatter):
        def custom_formatting_method(string):
            items = string.split("||")
            items = items[:2] + [get_caller_name(10)] + items[2:]
            return " || ".join(items)

        def format(self, record):
            default_formatted = logging.Formatter.format(self, record)
            return StandardFormatter.custom_formatting_method(default_formatted)
    
    class SimpleFormatter(logging.Formatter):
        def custom_formatting_method(string):
            return " || ".join(string.split("||"))

        def format(self, record):
            default_formatted = logging.Formatter.format(self, record)
            return SimpleFormatter.custom_formatting_method(default_formatted)

    return StandardFormatter(f"%(asctime)s||%(levelname)5s||%(message)s") if standard else SimpleFormatter(f"%(asctime)s||%(message)s")


class Logger():
    """
    This is a wrapper around the logging.Logger class which is used to insert calls for summary and error logging
    """
    def __init__(self, logger_instance):
        self.instance: logging.Logger = logger_instance
        self.handlers = self.instance.handlers
        self.error_log = logging.getLogger(Const.ErrorLogName)
        if not len(self.error_log.handlers):  # not already set up
            file_handler = logging.FileHandler(Const.ErrorLogName)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(GetLogFormatter(standard=False))
            self.error_log.addHandler(file_handler)
        self.error_log.setLevel(logging.INFO)
        self.session_logs = {}

    def setLevel(self, level: int | str):
        self.instance.setLevel(level)
        for handler in self.instance.handlers:
            handler.setLevel(level)

    def addHandler(self, hdlr: logging.Handler) -> None:
        return self.instance.addHandler(hdlr)

    def info(self, msg: object, *args: object, exc_info: _ExcInfoType = None, stack_info: bool = False, extra: Mapping[str, object] or None = None) -> None:
        return self.instance.info(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def error(self, msg: object, *args: object, exc_info: _ExcInfoType = None, stack_info: bool = False, extra: Mapping[str, object] or None = None) -> None:
        self.error_log.error(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
        return self.instance.error(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def warn(self, msg: object, *args: object, exc_info: _ExcInfoType = None, stack_info: bool = False, extra: Mapping[str, object] or None = None) -> None:
        return self.instance.warn(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def warning(self, msg: object, *args: object, exc_info: _ExcInfoType = None, stack_info: bool = False, extra: Mapping[str, object] or None = None) -> None:
        return self.instance.warning(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def exception(self, msg: object, *args: object, exc_info: _ExcInfoType = None, stack_info: bool = False, extra: Mapping[str, object] or None = None) -> None:
        self.error_log.exception(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
        return self.instance.exception(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def debug(self, msg: object, *args: object, exc_info: _ExcInfoType = None, stack_info: bool = False, extra: Mapping[str, object] or None = None) -> None:
        return self.instance.debug(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def critical(self, msg: object, *args: object, exc_info: _ExcInfoType = None, stack_info: bool = False, extra: Mapping[str, object] or None = None) -> None:
        return self.instance.critical(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)

    def summary(self, msg: object, session_id:str, *args: object, exc_info: _ExcInfoType = None, stack_info: bool = False, extra: Mapping[str, object] or None = None) -> None:
        if session_id not in self.session_logs:
            session_log_name = f"{session_id}{Const.SummaryLogPostfix}"
            self.session_logs[session_id] = logging.getLogger(session_log_name)
            file_handler = logging.FileHandler(session_log_name)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(GetLogFormatter(standard=False))
            self.session_logs[session_id].addHandler(file_handler)
            self.session_logs[session_id].setLevel(logging.INFO)
        self.session_logs[session_id].info(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
        return self.instance.info(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)


class ConsoleLogHandler(logging.StreamHandler):
    """
    Wrapper around StreamHandler to identify the handler in an existing logger instance
    """
    pass


def GetConsoleLogHandler() -> logging.StreamHandler:
    """
    Creates a ConsoleLogHandler instance that wraps sys.stdout so the logger instance will print to the console as well as file

    Returns:
        logging.StreamHandler: the stream handler instance to add to the logging.Logger handlers
    """
    consoleHandler = ConsoleLogHandler(sys.stdout)
    consoleHandler.setFormatter(GetLogFormatter())
    return consoleHandler


class TailLogHandler(logging.Handler):
    """
    A class that grabs log messages that come from logging.Logger if added to a logger instance's handlers
    """
    def __init__(self, log_queue):
        logging.Handler.__init__(self)
        self.log_queue = log_queue
    

    def emit(self, record:str):
        """
        a handler that kicks off anytime a log message goes through

        Args:
            record (str): a message to save
        """
        self.log_queue.append(self.format(record))


class TailLogger(object):
    """
    Tail logger is the class that keeps a running buffer of log messages if applied to a logger

    Args:
        object (_type_): _description_
    """
    def __init__(self, maxlen):
        self._log_queue = collections.deque(maxlen=maxlen)
        self._log_handler = TailLogHandler(self._log_queue)

    def contents(self) -> str:
        """
        returns the contents of the buffer

        Returns:
            str: the newline-joined list of log lines
        """
        return '\n'.join(self._log_queue)

    @property
    def log_handler(self):
        """
        property to contain the log handler

        Returns:
            TailLogHandler: the log handler
        """
        return self._log_handler


def get_tail_logger(logger:Logger | logging.Logger, format=True, max_lines=100) -> TailLogger:
    """
    Applies tail handler with optional formatting to a logging.Logger instance
    probably shouldn't be called by anyone other than get_mars_log

    Args:
        logger (Logger or logging.Logger): the logger instance
        format (bool, optional): whether or not to apply the MARS-style formatting. Defaults to True.
        max_lines (int, optional): how many lines to keep in the buffer. Defaults to 100.

    Returns:
        TailLogger: the captured buffer which contains the last n lines
    """
    buffer = TailLogger(max_lines)
    log_handler = buffer.log_handler
    logger.addHandler(log_handler)
    if format:
        log_handler.setFormatter(GetLogFormatter())
    
    return buffer


class ThreadExecutor(ThreadPoolExecutor):
    """
    Custom threadpoolexecutor class that has a little more control of threads and better shutdown
    """
    def __init__(self, *args, **kwargs):
        self.log = None
        super().__init__(*args, **kwargs)
        self.futures = []

    def submit(self, func: Callable, *args, **kwargs) -> Future:
        """
        submit a function for thread execution

        Args:
            func (Callable): the function

        Returns:
            Future: the pending future object
        """
        future = super().submit(func, *args, **kwargs)
        self.futures.append(future)
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
        for future in as_completed(self.futures, 5):
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
        self.futures = []
    
    def submit(self, func: Callable, *args, **kwargs) -> Future:
        """
        submit a function for process execution

        Args:
            func (Callable): the function

        Returns:
            Future: the pending future object
        """
        future = super().submit(func, *args, **kwargs)
        self.futures.append(future)
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
        for future in as_completed(self.futures, 5):
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


class ResourceManager:
    """
    Class to manage system resources
    For now, this just contains thread and process pool executors
    planned future support includes
        - analyzing system resources/capabilities
        - intelligently managing threads/processes
        - distributing jobs between instances of services
    """
    def __init__(self) -> None:
        self.running = True
        self.thread_executor = ThreadExecutor()
        self.process_executor = ProcessExecutor()
        atexit.register(self.shutdown)
        self.log = None
    
    def _assign_logger(self, log):
        """
        assigns a log object to the resource manager and sub executors

        Args:
            log (Logger): the log obtained by get_mars_log()
        """
        self.log = self.log or log
        self.thread_executor.log = self.log
        self.process_executor.log = self.log

    def submit(self, submission:Callable, *args, thread:bool=True, **kwargs) -> Future:
        """
        submit a function for a new thread or process if thread=False

        Args:
            submission (Callable): the function to submit for parallelization
            thread (bool, optional): whether to use a thread instead of a process. Defaults to True.

        Raises:
            Exception: error submitting the job

        Returns:
            Future: the future containing the job, meant for tracking and later result checking
        """
        try:
            if thread:
                return self.thread_executor.submit(submission, *args, **kwargs)
            else:
                return self.process_executor.submit(submission, *args, **kwargs)
        except Exception as submission_exception:
            raise Exception(f"Unable to submit {submission.__name__}: '{submission_exception}'")

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


def get_mars_log(logger:Logger | logging.Logger=None, log_name:str=Const.MarsLogName, log_level:int | str=None, format:bool=True, get_tail=False, max_lines:int=100) -> Logger | Tuple[Logger, TailLogger]:
    """
    Gets the universal mars logging instance

    if you want to get a different log, then you need to pass a different log_name parameter, e.g. get_mars_log(log_name=f"{__file__}.log")

    Args:
        logger (Logger or logging.Logger, optional): the logger instance if there already is one, will format it. Defaults to None.
        log_name (str, optional): the expected name of the log file. Defaults to Const.MarsLogName.
        log_level (int or str, optional): the level at which to allow lines to be written. Defaults to None.
        format (bool, optional): whether or not to set the format of the log to the MARS style log lines. Defaults to True.
        get_tail (bool, optional): whether or not to return the log line buffer. Defaults to False.
        max_lines (int, optional): how many lines to keep buffered, useful for services to display logs. Defaults to 100.

    Returns:
        Logger or Tuple[Logger, TailLogger]: the logger and optionally the log buffer
    """
    logger = Logger(logger if logger else logging.getLogger(log_name))
    # if not len(logger.handlers):  # not already set up
    #     file_handler = logging.FileHandler(log_name)
    #     file_handler.setLevel(log_level if log_level else logging.INFO)
    #     if format:
    #         file_handler.setFormatter(GetLogFormatter())
    #     logger.addHandler(file_handler)
    if not any(isinstance(handler, ConsoleLogHandler) for handler in logger.handlers):
        console_handler = GetConsoleLogHandler()
        if format:
            console_handler.setFormatter(GetLogFormatter())
            console_handler.setLevel(log_level if log_level else logging.INFO)
        logger.addHandler(console_handler)
    if not any(isinstance(handler, RotatingFileHandler) for handler in logger.handlers):
        rotating_log_handler = RotatingFileHandler(log_name, maxBytes=10_000_000, backupCount=10,)
        if format:
            rotating_log_handler.setFormatter(GetLogFormatter())
        rotating_log_handler.setLevel(log_level if log_level else logging.INFO)
        logger.addHandler(rotating_log_handler)
    if log_level:
        logger.setLevel(log_level)
    ResourceManager._assign_logger(logger)
    if not get_tail:
        return logger
    else:
        tail = get_tail_logger(logger, format=format, max_lines=max_lines)
        return logger, tail


class Schemas(dict):
    """
    Consolidates schema data

    builds an object capable of access via field access or dict item access regardless of extension
    the following examples all load the same schema
    Schemas.example_schema
    Schemas.example_schema.json
    Schemas["example_schema"]
    Schemas["example_schema.json"]
    """
    def __init__(self):
        log = get_mars_log()
        self.all_schemas = []
        schema_path = safe_path(os.path.join(get_project_root(), Const.Directories.Schemas))
        schema_paths = [schema_path]
        project_path = safe_path(os.path.join(get_project_root(), Const.Directories.Schemas))
        if os.path.exists(project_path):
            schema_paths.append(project_path)
        for path in schema_paths:
            for file in path.iterdir():
                if file.name.endswith(".py"):
                    schema = import_module_from_path(file).schema
                elif file.name.endswith(".json"):
                    with open(file, 'r') as schema:
                        schema = json.loads(schema.read())
                else:
                    if "__pycache__" not in f"{file}":
                        log.warn(f"Skipping non-functional file in schema dir: '{file}'")
                jsonschema.Draft202012Validator.check_schema(schema)
                schema_file = os.path.basename(file.name)
                self[schema_file] = schema
                no_ext = os.path.splitext(schema_file)[0]
                self[no_ext] = schema
                self.__setattr__(no_ext, schema)
                self.all_schemas.append(no_ext)


Schemas = Schemas()


def sanitize(data:str, regex_string=RegexStrings.AlphaNumeric, double_dash_exempt:bool=False) -> bool:
    """
    Determines if a string is sanitary

    Args:
        data (str): string to check
        regex_string (_type_, optional): the regex check to make. Defaults to RegexStrings.AlphaNumeric.
        double_dash_exempt (bool, optional): whether or not -- can be ignored, e.g. not SQL. Defaults to False.

    Returns:
        bool: whether or not the string is sanitary
    """
    match = re.match(regex_string, data)
    block_drop = re.findall(RegexStrings.BlockDrop, data)
    block_delete = re.findall(RegexStrings.BlockDelete, data)
    block_sql = None if double_dash_exempt else re.findall(RegexStrings.BlockSqlComment, data)
    return match and not block_drop and not block_sql and not block_delete


def sanitize_json(instance: dict | bool | list | str) -> bool:
    """
    Sanitizes an instance using the sanitation functionality

    Args:
        instance (dictorbool): an object to check, should be json-ish

    Returns:
        bool: true if data is valid
    """
    def sub_sanitize(sub_instance):
        if isinstance(sub_instance, dict):
            for k, v in sub_instance.items():
                if not sanitize(f"{k}", RegexStrings.Variable):  # allow letters, numbers, space, and underscores only in keys
                    raise jsonschema.ValidationError(f"Key {k} is not sanitary!")
                if not sanitize(f"{v}", RegexStrings.PathLike):  # allow anything that's allowed in a path in a variable
                    raise jsonschema.ValidationError(f"dict val {v} is not sanitary!")
        elif isinstance(sub_instance, list):
            for item in sub_instance:
                if not sanitize(f"{item}", RegexStrings.PathLike):  # allow anything that's allowed in a path in a variable
                    raise jsonschema.ValidationError(f"list item {item} is not sanitary!")
        else:
            if not sanitize(f"{sub_instance}", RegexStrings.PathLike):  # allow anything that's allowed in a path in a variable
                raise jsonschema.ValidationError(f"Value {sub_instance} is not sanitary!")
        return True
    return sub_sanitize(instance)


def custom_schema_validation(instance: dict | bool, schema: dict) -> None:
    """
    Wraps the jsonschma's validate function with some better error handling, especially useful in the case of custom error messages

    Args:
        instance (dict or bool): a json-like object to validate, generally a dict
        schema (dict): the schema to use to validate the instance

    Raises:
        SchemaValidationError: error validating the schema
    """
    try:
        jsonschema.validate(instance, schema)
    except Exception as validation_exception:
        err = f"{validation_exception}"
        instance_str = f"{instance}"
        if len(instance_str) > 32:  # need to shrink this down
            instance_str = f"{instance_str[:32]}..."
        if "error message" in err:
            err_start = err.find("error message")+15
            err = err[err_start:]
            err_end = err.find("\n", err_start)
            err = err[:err_end]
            pattern_str = ""
            if "'pattern'" in err:
                pattern_start = err.find("'pattern'")
                pattern = err[pattern_start+11:].strip()
                err = err[:pattern_start].strip()
                pattern_str = f"\nUse regex pattern: {pattern}"
            raise jsonschema.ValidationError(f"Error validating {instance_str} because {err}{pattern_str}")
        else:
            raise jsonschema.ValidationError(f"Error validating {instance_str}\n{err}")


def add_default_values_to_missing_keys(data: dict, schema: dict, key: str="") -> dict:
    """
    Recursively adds default values to a dictionary for missing keys based upon a given schema
    Args:
        data:
        schema:

    Returns:
        dict: an updated dictionary that has the defaults values pulled from the schema for any missing keys
    """
    default_values = schema.get("default", False)
    if schema.get("type") == "object" and not default_values:
        schema_keys = list(schema.get("properties", {}).keys())
        seen_keys = list(data.keys())
        missing_keys = list(set(schema_keys).difference(seen_keys))

        for key in missing_keys:
            data[key] = add_default_values_to_missing_keys(data=data.get(key, {}), schema=schema.get("properties", {}).get(key, {}), key=key)
    elif schema.get("type") == "object":
        data[key] = default_values
    else:
        data = default_values
    return data


def load_json_file_2_dict(json_file: str | Path, comment_remove: bool=True, expand_path: bool=True, fix: bool=True, log=None) -> dict:
    """
    Returns a dictionary created based on the given json file
    Args:
        json_file: input json file
        comment_remove: remove all the comment from the given JSON file
        expand_path: whether to expand path variables such as %%MARS_DIR%% to their proper paths
        fix: whether to attempt to fix broken json
        log: log used to report any failures

    Returns:
        dict: a dictionary generated from the json file
    """
    try:
        get_mars_log().debug(f"Loading json file {json_file}")
        with open(json_file, 'r', encoding="utf-8") as f:
            line = re.sub(u'[\u201c\u201d]', '"', f.read())  # read and convert all the fancy quotes to neutral quotes
            line = re.sub(u'[\u2018\u2019]', "\'", line)  # read and convert all the open/close quotes to neutral quotes
            # if comment_remove:
            #     line = remove_comments(line)
            return json.loads(line) #if not expand_path else expand_mars_path_vars(json.loads(line))
    except json.decoder.JSONDecodeError as ex_data:
        # if fix:
        #     return fix_json_decode_error(line, ex_data, expand_path, log=log)
        # else:
        raise Exception("Did you leave an extra comma and forget to add another value in '" +
                        json_file + "'?: " + str(ex_data)) from ex_data
    except Exception as file_exception:
        raise Exception("load_json_file_2_dict error reading file " + json_file + ". :" + str(file_exception))


def load_json(to_load: str | dict | Path) -> dict:
    """
    Loads json data either by loading the file from the given path if to_load is a string, or directly loads it from
    to_load it is a dictionary it returns to_load. Performs a sanitization check the json once it has been
    loaded.
    Args:
        to_load: either the json itself to load or the path to load the json file from

    Returns:
        dict: a loaded and sanitized json in dict format if the sanitization check indicates the loaded json is
         valid otherwise returns an empty dictionary
    """
    json_data = {}
    if isinstance(to_load, dict):
        json_data = to_load
    elif (isinstance(to_load, str) and '{' not in to_load) or isinstance(to_load, Path):
        to_load = safe_path(to_load)
        if os.path.exists(to_load) and str(to_load).endswith(".json"):
            json_data = load_json_file_2_dict(to_load)
    elif isinstance(to_load, str) and '{' in to_load:
        json_data = json.loads(to_load)
    try:
        is_sanitized = sanitize_json(json_data) # FIXME add back in after fixing RegExStr to use for keys
    except Exception as sanitization_exe:
        return {}
    if is_sanitized:
        return json_data
    else:
        return {}


if __name__ == "__main__":
    # parse cfg files - load_json_file_2_dict
    # load the syscheck results - need custom parser 
    # determine which tasks need to be executed - mapping from errors to action
    # execute tasks - ssh using the intervention library
    # load results to output file
    # report results - API
    pass