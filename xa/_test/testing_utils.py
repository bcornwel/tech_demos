"""
Utilities for general testing purposes
"""

from logging import Logger
from typing import Callable, Sequence, Tuple


def clear_logs(files: list = None):
    """
    Clears all logs, used before testing to ensure logs are coherent

    Add your test logs here, or call clear_logs with the files to clear
    e.g. clear_logs(["errors.log", "xa.log"])  # clears errors.log and xa.log from root
    Args:
        files (list or str, optional): list of files to clear logs of. Expecting file names to match log names, or to match a file which has .log appended. Defaults to None.
    """
    import os
    from core.definitions import FileNames
    from infra.file_utils import get_project_root, safe_path
    root = get_project_root()
    main_log = os.path.join(root, FileNames.LogName)
    error_log = os.path.join(root, FileNames.ErrorLogName)
    to_clear = [
        error_log,  # error log should be cleared so as to not mistake error logs from previous runs
        main_log  # standard xa.log should be cleared since it's used by almost all code unless explicitly stated otherwise
    ]
    if isinstance(files, str):
        files = [files]
    for file in files:
        safe_file = safe_path(file).with_suffix(".log") # change the ending to ensure we only delete logs, in case __file__ is passed, which will end in .py
        if os.path.exists(safe_file):
            to_clear.append(safe_file)
        if os.path.exists(safe_file.name):
            if not safe_file.samefile(safe_file.name):
                to_clear.append(safe_file.name)  # same log, different folder. clear both just in case
    for log in to_clear:
        if os.path.exists(log):
            try:
                os.remove(log)
            except Exception as e:
                print(f"Unable to clear '{log}': {e}")


def get_all_functions(layers=1) -> Sequence[Callable]:
    """
    Gets all functions in current scope
    e.g. if you call this with layers=1, it will get all functions in the calling method/file

    Args:
        layers (int, optional): how many stack layers. This is VERY important to get right. Defaults to 1.

    Returns:
        Sequence[Callable]: the list of all test functions in the scope
    """
    try:
        import inspect
        frm = inspect.stack()[layers]
        mod = frm[0]
        funcs = [(name, func) for name, func in mod.f_locals.items() if callable(func)]
        return funcs
    except Exception as ex_data:
        try:
            name = mod.f_locals.__name__
        except:
            name = "a test module"
        print(f"Error getting functions from {mod.f_locals['__name__']}: {str(ex_data)}")


def get_all_tests(funcs: Sequence[Callable]=None, layers=2) -> Sequence[Tuple[str, Callable]]:
    """
    Gets all test functions in current scope

    Args:
        funcs (Sequence[Callable], optional): if get_all_functions has been called already, reuse those functions. Defaults to None.
        layers (int, optional): how many stack layers. This is VERY important to get right. Defaults to 2.

    Returns:
        Sequence[Tuple[str, Callable]]: the list of tuples (name, func) for each method in the parent module
    """    
    if funcs is None:
        funcs = get_all_functions(layers=layers)
    return [(name, func) for name, func in funcs if str(name).startswith("test_")]


def get_all_failing_tests(funcs:Sequence[Callable]=None, layers=2) -> Sequence[Tuple[str, Callable]]:
    """
    gets the list of failing tests from the calling module

    Args:
        funcs (Sequence[Callable], optional): if get_all_functions has been called already, reuse those functions. Defaults to None.
        layers (int, optional): how many stack layers. This is VERY important to get right. Defaults to 2.

    Returns:
        Sequence[Tuple[str, Callable]]: the list of tuples (name, func) for each method in the parent
    """
    if funcs is None:
        funcs = get_all_functions(layers=layers)
    return [(name, func) for name, func in funcs if str(name).startswith("fail_")]


def run_all_tests(logger:Logger=None, print_results:bool=True, log_results:bool=True, count:int=1):
    """
    Runs all tests in a file

    Args:
        logger (logging.Logger, optional): Logger object. Defaults to None.
        print_results (bool, optional): whether or not to print to console. Defaults to True.
        log_results (bool, optional): whether or not to print to log. Defaults to True.
        count (int, optional): how many times to run the list of tests. Defaults to 1.

    Raises:
        Exception: test error
    """
    import traceback
    import logging
    from infra.log_utils import get_caller_name
    err = False
    name = "a test module"
    try:
        clear_logs(get_caller_name(2))
        logger = None if not log_results else logger if logger else logging.getLogger()

        def print_out(msg):
            if print_results:
                print(msg)
            if log_results:
                logger.info(msg)

        try:
            name = get_caller_name(2)
        except Exception as mod_name_exception:
            msg = f"Error getting module name. Running from {__file__}."
            logger.warn(msg)
        funcs = get_all_tests(layers=3)
        test_cnt = len(funcs)
        print_out(f"Running {test_cnt} tests in {name} {count} time(s)")
        for i in range(count):
            for func_info in funcs:
                print_out(f"{'=' * (20 + len(func_info[0]))}")  # prints a line of '=' equal in size to the line below
                print_out(f"Running unit test '{func_info[0]}' iteration #{i+1} of {count}")
                status = "Pass"
                try:
                    func_info[1]()  # call the function
                except Exception as ex_data:
                    status = "Fail"
                    print_out(f"Exception encountered in '{func_info[0]}':\n{traceback.format_exc()}")
                    err = True
                print_out(f"Test '{func_info[0]}' {status}ed")
                print_out(f"{'=' * (15 + len(func_info[0]) + len(status))}")
    except Exception as run_all_tests_exception:
        print(f"There was an issue running all tests from {name}:\n{traceback.format_exc()}")
        err = True
    if err:
        raise Exception(f"There was an issue running all tests from {name}. See log lines above")


if __name__ == "__main__":
    from core.definitions import Strings
    print(Strings.NotStandalone)
