import collections
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import sys
from typing import Mapping, Tuple


from definitions import FileNames
from utils import get_caller_name, get_project_root, ResourceManager


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
        self.error_log = logging.getLogger(f"{Path(get_project_root(), FileNames.ErrorLogName)}")
        if not len(self.error_log.handlers):  # not already set up
            file_handler = logging.FileHandler(f"{Path(get_project_root(), FileNames.ErrorLogName)}")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(GetLogFormatter(standard=False))
            self.error_log.addHandler(file_handler)
        self.error_log.setLevel(logging.INFO)
        self.instance.setLevel(logging.INFO)

    def setLevel(self, level: int | str):
        self.instance.setLevel(level)
        for handler in self.instance.handlers:
            handler.setLevel(level)

    def addHandler(self, hdlr: logging.Handler) -> None:
        return self.instance.addHandler(hdlr)

    def info(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] | None = None) -> None:
        return self.instance.info(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def error(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] | None = None) -> None:
        self.error_log.error(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
        return self.instance.error(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def warn(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] | None = None) -> None:
        return self.instance.warn(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def warning(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] | None = None) -> None:
        return self.instance.warning(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def exception(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] | None = None) -> None:
        self.error_log.exception(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
        return self.instance.exception(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def debug(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] | None = None) -> None:
        return self.instance.debug(msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)
    
    def critical(self, msg: object, *args: object, exc_info: BaseException = None, stack_info: bool = False, extra: Mapping[str, object] | None = None) -> None:
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
        log_handler.setFormatter(GetLogFormatter())
    
    return buffer


def dump_log_data_to_dir(logger:Logger, dir_name:str | Path):
    """
    Copies log files to the specified directory

    Args:
        logger (Logger): the logging object
        dir_name (str | Path): the directory to store logs
    """
    os.makedirs(dir_name, mode=777, exist_ok=True)
    shutil.copy(Path(get_project_root(), FileNames.LogName), dir_name)  # for some reason this is complaining permission is denied
    shutil.copy(Path(get_project_root(), FileNames.ErrorLogName), dir_name)


def get_log(logger:Logger | logging.Logger=None, log_name:str=f"{Path(get_project_root(), FileNames.LogName)}", log_level:int | str=None, format:bool=True, get_tail=False, max_lines:int=100) -> Logger | Tuple[Logger, TailLogger]:
    """
    Gets the universal logging instance

    if you want to get a different log, then you need to pass a different log_name parameter, e.g. get_log(log_name=f"{__file__}.log")

    Args:
        logger (Logger or logging.Logger, optional): the logger instance if there already is one, will format it. Defaults to None.
        log_name (str, optional): the expected name of the log file. Defaults to Const.LogName.
        log_level (int or str, optional): the level at which to allow lines to be written. Defaults to None.
        format (bool, optional): whether or not to set the format of the log. Defaults to True.
        get_tail (bool, optional): whether or not to return the log line buffer. Defaults to False.
        max_lines (int, optional): how many lines to keep buffered, useful for services to display logs. Defaults to 100.

    Returns:
        Logger or Tuple[Logger, TailLogger]: the logger and optionally the log buffer
    """
    try:
        os.remove(log_name)  # clear the healing.log file just in case
    except:
        pass
    try:
        os.remove(f"{Path(get_project_root(), FileNames.ErrorLogName)}")  # clear the errors.log file just in case
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


if __name__ == "__main__":
    from definitions import Strings
    print(Strings.NotStandalone)
