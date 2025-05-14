"""
This file contains functionality for managing logs
"""


import collections
import datetime
import inspect
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import sys
from typing import Mapping


from core.definitions import FileNames
from infra.proc_utils import ResourceManager
from infra.file_utils import get_output_root


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


def str_to_log_level(s_lvl:str) -> int:
    """
    Converts a logging string name to level e.g. INFO to logging.INFO

    Args:
        s_lvl (str): a string name e.g. INFO

    Raises:
        Exception: unable to find the log level

    Returns:
        int: the logging level
    """
    try:
        return logging._nameToLevel[s_lvl]
    except Exception as conversion_exception:
        msg = f"Unable to find log level from name '{s_lvl}'"
        logging.getLogger(f"{Path(get_output_root(), FileNames.LogName)}").error(msg, stack_info=True)
        raise Exception(msg)


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
        return f"{func_name}"


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
            items = items[:2] + [get_caller_name(11)] + items[2:]
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

    return StandardFormatter(f"%(asctime)s||%(levelname)5s||%(message)s") if standard else SimpleFormatter(f"%(asctime)s||%(levelname)5s||%(message)s")


class Logger():
    """
    This is a wrapper around the logging.Logger class which is used to insert calls for summary and error logging
    """
    def __init__(self, logger_instance):
        self.instance: logging.Logger = logger_instance
        self.handlers = self.instance.handlers
        self.error_log = logging.getLogger(f"{Path(os.path.dirname(self.instance.name), FileNames.ErrorLogName)}")
        if not len(self.error_log.handlers):  # not already set up
            file_handler = logging.FileHandler(f"{Path(os.path.dirname(self.instance.name), FileNames.ErrorLogName)}")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(GetLogFormatter(standard=True))
            self.error_log.addHandler(file_handler)
        self.error_log.setLevel(logging.INFO)
        self.instance.setLevel(logging.INFO)

        #inject STDOUT and STDERR levels/calls into logging
        logging.addLevelName(19, "STDERR")
        logging.addLevelName(18, "STDOUT")
            

    def setLevel(self, level: int):
        self.instance.setLevel(level)
        for handler in self.instance.handlers:
            handler.setLevel(level)

    def addHandler(self, hdlr: logging.Handler) -> None:
        return self.instance.addHandler(hdlr)

    def info(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] = None) -> None:
        return self.instance.info(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def error(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] = None) -> None:
        self.error_log.error(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
        return self.instance.error(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def warn(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] = None) -> None:
        return self.instance.warn(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def warning(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] = None) -> None:
        return self.instance.warning(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def exception(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] = None) -> None:
        self.error_log.exception(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
        return self.instance.exception(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def debug(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] = None) -> None:
        return self.instance.debug(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)

    def stdout(self, msg: object, *args, **kwargs) -> None:
        return self.instance._log(18, msg, args, **kwargs)

    def stderr(self, msg: object, *args, **kwargs) -> None:
        return self.instance._log(19, msg, args, **kwargs)

    def critical(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] = None) -> None:
        return self.instance.critical(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)


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
    consoleHandler.setFormatter(GetLogFormatter(standard=False))
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


def get_tail_logger(logger:Logger, format=True, max_lines=100) -> TailLogger:
    """
    Applies tail handler with optional formatting to a logging.Logger instance
    probably shouldn't be called by anyone other than get_log

    Args:
        logger (Logger or logging.Logger): the logger instance
        format (bool, optional): whether or not to apply formatting. Defaults to True.
        max_lines (int, optional): how many lines to keep in the buffer. Defaults to 100.

    Returns:
        TailLogger: the captured buffer which contains the last n lines
    """
    buffer = TailLogger(max_lines)
    log_handler = buffer.log_handler
    logger.addHandler(log_handler)
    if format:
        log_handler.setFormatter(GetLogFormatter(standard=False))
    
    return buffer


def dump_log_data_to_dir(logger:Logger, dir_name:str):
    """
    Copies log files to the specified directory

    Args:
        logger (Logger): the logging object
        dir_name (str | Path): the directory to store logs
    """
    os.makedirs(dir_name, mode=0o777, exist_ok=True)
    shutil.copy(Path(get_output_root(), FileNames.LogName), dir_name)  # for some reason this is complaining permission is denied
    shutil.copy(Path(get_output_root(), FileNames.ErrorLogName), dir_name)


def get_log(logger:Logger=None, log_name:str=f"{Path(get_output_root(), FileNames.LogName)}", log_level:int=None, format:bool=True, verbose=False, get_tail=False, max_lines:int=100) -> Logger:
    """
    Gets the universal logging instance

    if you want to get a different log, then you need to pass a different log_name parameter, e.g. get_log(log_name=f"{__file__}.log")

    Args:
        logger (Logger or logging.Logger, optional): the logger instance if there already is one, will format it. Defaults to None.
        log_name (str, optional): the expected name of the log file. Defaults to Const.LogName.
        log_level (int or str, optional): the level at which to allow lines to be written. Defaults to None.
        format (bool, optional): whether or not to set the format of the log. Defaults to True.
        verbose (bool, optional): whether or not to set the verbose setting in the log. Defaults to False.
        get_tail (bool, optional): whether or not to return the log line buffer. Defaults to False.
        max_lines (int, optional): how many lines to keep buffered, useful for services to display logs. Defaults to 100.

    Returns:
        Logger or Tuple[Logger, TailLogger]: the logger and optionally the log buffer
    """
    try:
        os.remove(log_name)  # clear the xa.log file just in case
    except:
        pass
    try:
        os.remove(str(Path(os.path.dirname(log_name), FileNames.ErrorLogName)))  # clear the errors.log file just in case
    except:
        pass
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
            console_handler.setFormatter(GetLogFormatter(standard=verbose))
            console_handler.setLevel(log_level if log_level else logging.INFO)
        logger.addHandler(console_handler)
    if not any(isinstance(handler, RotatingFileHandler) for handler in logger.handlers):
        rotating_log_handler = RotatingFileHandler(log_name, maxBytes=10_000_000, backupCount=10,)
        if format:
            rotating_log_handler.setFormatter(GetLogFormatter(standard=True))
        rotating_log_handler.setLevel(log_level if log_level else logging.INFO)
        logger.addHandler(rotating_log_handler)
    if log_level:
        logger.setLevel(log_level)
    if verbose:
        logger.setLevel(logging.DEBUG)
    ResourceManager._assign_logger(logger)
    if not get_tail:
        return logger
    else:
        tail = get_tail_logger(logger, format=format, max_lines=max_lines)
        return logger, tail


if __name__ == "__main__":
    from core.definitions import Strings
    print(Strings.NotStandalone)