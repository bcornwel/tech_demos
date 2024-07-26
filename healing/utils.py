import atexit
from concurrent.futures import as_completed, Future, ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures._base import RUNNING
import datetime
import inspect
import json
import jsonschema
import logging
import os
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Callable


from definitions import *


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
        logging.getLogger(FileNames.LogName).error(msg, stack_info=True)
        raise Exception(msg)


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
            log (Logger): the log obtained by get_log()
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


# class Schemas(dict):
#     """
#     Consolidates schema data

#     builds an object capable of access via field access or dict item access regardless of extension
#     the following examples all load the same schema
#     Schemas.example_schema
#     Schemas.example_schema.json
#     Schemas["example_schema"]
#     Schemas["example_schema.json"]
#     """
#     def __init__(self):
#         log = get_log()
#         self.all_schemas = []
#         schema_path = safe_path(os.path.join(get_project_root(), Const.Directories.Schemas))
#         schema_paths = [schema_path]
#         project_path = safe_path(os.path.join(get_project_root(), Const.Directories.Schemas))
#         if os.path.exists(project_path):
#             schema_paths.append(project_path)
#         for path in schema_paths:
#             for file in path.iterdir():
#                 if file.name.endswith(".py"):
#                     schema = import_module_from_path(file).schema
#                 elif file.name.endswith(".json"):
#                     with open(file, 'r') as schema:
#                         schema = json.loads(schema.read())
#                 else:
#                     if "__pycache__" not in f"{file}":
#                         log.warn(f"Skipping non-functional file in schema dir: '{file}'")
#                 jsonschema.Draft202012Validator.check_schema(schema)
#                 schema_file = os.path.basename(file.name)
#                 self[schema_file] = schema
#                 no_ext = os.path.splitext(schema_file)[0]
#                 self[no_ext] = schema
#                 self.__setattr__(no_ext, schema)
#                 self.all_schemas.append(no_ext)


# Schemas = Schemas()


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


def sanitize_dict(instance: dict | bool | list | str) -> bool:
    """
    Sanitizes an instance using the sanitation functionality

    Args:
        instance (dictorbool): an object to check, should be json/dict-ish

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
                sub_sanitize(v)
        elif isinstance(sub_instance, list):
            for item in sub_instance:
                if not sanitize(f"{item}", RegexStrings.PathLike):  # allow anything that's allowed in a path in a variable
                    raise jsonschema.ValidationError(f"list item {item} is not sanitary!")
                sub_sanitize(item)
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
        expand_path: whether to expand path variables such as %%HEALING_DIR%% to their proper paths
        fix: whether to attempt to fix broken json
        log: log used to report any failures

    Returns:
        dict: a dictionary generated from the json file
    """
    try:
        with open(json_file, 'r', encoding="utf-8") as f:
            line = re.sub(u'[\u201c\u201d]', '"', f.read())  # read and convert all the fancy quotes to neutral quotes
            line = re.sub(u'[\u2018\u2019]', "\'", line)  # read and convert all the open/close quotes to neutral quotes
            # if comment_remove:
            #     line = remove_comments(line)
            return json.loads(line) #if not expand_path else expand_path_vars(json.loads(line))
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
        is_sanitized = sanitize_dict(json_data) # FIXME add back in after fixing RegExStr to use for keys
    except Exception as sanitization_exe:
        return {}
    if is_sanitized:
        return json_data
    else:
        return {}


def load_space_delimited_file(to_load: str | Path, headers=None, header_line=0, use_hashes=False) -> dict:
    """
    Loads space delimited data by loading the file from the given path.
    Performs a sanitization check the dict once it has been loaded.
    Args:
        to_load: the path to load the file from
        headers: optional headers in which case don't auto-generate the header info from the file
        header_line: the line number which contains the headers for the data in the file
        use_hashes: whether or not to include hashes in row names to separate non-unique names

    Returns:
        dict: a loaded and sanitized dict if the sanitization check indicates the loaded data is valid otherwise returns an empty dictionary
    """
    content = open(to_load, 'r').readlines()
    table = dict()
    if not headers:
        headers = [re.sub(RegexStrings.FriendlyName, '', h).strip() for h in re.split(RegexStrings.SpaceDelimiter, content[header_line].strip('\n').strip())]
        item_count = len(headers)
    else:
        header_line = -1
        item_count = len(headers)
    for i, row in enumerate(content[header_line+1:]):
        row = re.sub(RegexStrings.AnsiEscapes, '', row).strip('\n').strip()  # remove formatting (colors, newlines, and extra spaces)
        if row == '':
            continue
        row_data = re.split(RegexStrings.SpaceDelimiter, row)
        assert item_count == len(row_data), f"Data in row {i} of file {to_load} does not match headers"
        name = f"{re.sub(RegexStrings.FriendlyName, '', row_data[0])}"
        if use_hashes:
            name += f"_{str(hash(str(row_data)))[-4:]}"
        table[name.strip()] = {k: re.sub(RegexStrings.FriendlyName, '', v).strip() for k, v in zip(headers, row_data)}
    return table if sanitize_dict(table) else {}  # TODO: validate schema if one is available