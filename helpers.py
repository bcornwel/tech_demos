import collections
import functools
import inspect
import json
import logging
import platform
import sys
import time
import jsonschema
import re
import os
from typing import Any, Callable


class DebugTriggers:
    FunctionPrinting = True
    Timing = True


class SchemaValidationError(Exception):
    pass


class Const:
    class Regex:
        Alpha = r"[a-zA-Z]"
        Numeric = r"[\.0-9]"
        AlphaNumeric = r"[a-zA-Z\.0-9]"
        Variable = r"[a-zA-Z\.0-9_]"
        PathLike = r"[a-zA-Z0-9_\.]"
        Tuple = r"[a-zA-Z0-9_\(\)\,]"
        BlockDrop = r"(?i)Drop (index|constraint|table|column|primary|foreign|check|database|view)"
        BlockDelete = r"(?i)Delete from"
        BlockSqlComment = r"--"
        Job_ID = r"^\d{6}_\d_\d_\d_\d{8}"


def exception_decorator(func: Callable, logger: logging.Logger) -> Callable:
    """
    wraps a function in an exception handler to log that it failed

    Args:
        func (Callable): function to wrap

    Returns:
        Callable: wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            return ret
        except Exception as e:
            # logger.error(f"Method failed: {e}")
            print(f"Method failed: {e}")
            raise e
    return wrapper


def debug_decorator(func: Callable) -> Callable:
    """
    Decorates functions with debug prints and timing functionality (if enabled in the GlobalTriggers class)

    Args:
        func (function): the function to decorate

    Returns:
        function: the wrapped function containing the original function with the debug and timing functionality
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if DebugTriggers.FunctionPrinting:
            msg = ""
            func_name = f"{func}"
            if func_name.startswith("<function"):
                func_name = func_name.split()[1]
            try:
                stack = inspect.stack()[1]
            except:
                pass
            try:
                # this line uses reflection to get the name of the class that calls this line
                calling_object = str(stack[0].f_locals["self"].__class__.__name__)
                # this line uses reflection to get the name of the function inside the class that calls this line
                object_function = str(stack[3])
                # this line uses reflection to get the name of the function that calls this log line
                msg = f"Running {func_name} in {calling_object}.{object_function}"
            except Exception as class_exception:  # failed to get the class name that called this method. oh well
                msg = f"Running {func_name}"
            print(msg)
        if DebugTriggers.Timing:
            start_time = time.perf_counter()
        ret = func(*args, **kwargs)
        if DebugTriggers.Timing:
            end_time = time.perf_counter()
            run_time = end_time - start_time
            print(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        if DebugTriggers.FunctionPrinting:
            print(f"Done r{msg[1:]}")
        return ret

    return wrapper


def decorate_all_methods(decorator: Callable, *args, **kwargs) -> Callable:
    """
    Decorates all the methods in a class (includes static methods)

    Args:
        decorator (function): the decorator to apply to the methods
    """
    def decorate(cls):
        for attr in cls.__dict__:
            gattr = getattr(cls, attr)
            if callable(gattr):
                setattr(cls, attr, decorator(gattr, *args, **kwargs))
        return cls
    return decorate


def client_decorator(func: Callable) -> Callable:
    """
    prints the return value, meant for server functions to see what data is being returned

    Args:
        func (Callable): function to wrap

    Returns:
        Callable: wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        print(func.__name__, "returned", f"{ret}")
        return ret
    return wrapper

class RegexValidator():
    def validate(self, instance: dict or bool) -> dict:
        def sub_validate(sub_instance):
            if isinstance(sub_instance, dict):
                for k, v in sub_instance.items():
                    if not self.sanitize(f"{k}", Const.Regex.Variable):  # allow letters, numbers, and underscores only in keys
                        raise jsonschema.ValidationError(f"Key {k} is not sanitary!")
                    sub_validate(v)
            elif isinstance(sub_instance, list):
                for item in sub_instance:
                    sub_validate(item)
            else:
                if not self.sanitize(f"{sub_instance}", Const.Regex.PathLike):  # allow anything that's allowed in a path in a variable
                    raise jsonschema.ValidationError(f"Value {sub_instance} is not sanitary!")
        return sub_validate(instance)

    def sanitize(self, data, regex_string=Const.Regex.AlphaNumeric, double_dash_exempt=False):
        match = re.match(regex_string, data)
        block_drop = re.match(Const.Regex.BlockDrop, data)
        block_delete = re.match(Const.Regex.BlockDelete, data)
        block_sql = None if double_dash_exempt else re.match(Const.Regex.BlockSqlComment, data)
        return match and not block_drop and not block_sql and not block_delete


def register_name(name: str, registry: dict) -> Callable:
    """
    Registers a function in the registry provided

    Args:
        name (string): step name
        registry (dict): dictionary to register the function in
    Returns the wrapped function
    """
    def _register(func):
        registry[name] = func
        return func
    return _register


def register_idx(idx: str, registry: set or list, default:Any = None) -> Callable:
    """
    Registers a function in the registry provided

    Args:
        name (string): step name
        registry (set): set to register the function in
    Returns the wrapped function
    """
    def _register(func):
        for i in range(len(registry), idx+1):
            if isinstance(registry, set):
                registry.add(default)
            elif isinstance(registry, list):
                registry.append(default)
            else:
                raise Exception(f"Uncertain how to append items to {type(registry)}!")
        registry[idx] = func
        return func
    return _register

class Schemas:
    _ExampleSchema = {
        "type": "object",
        "properties": {
            "example name": {
                "type": "string",
                "pattern": Const.Regex.AlphaNumeric,
                "error message": f"This data should match the format {Const.Regex.AlphaNumeric}"
            },
            "example tuple": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "prefixItems": [
                    {
                        "type": "string"
                    },
                    {
                        "type": "number"
                    }
                ]
            },
            "example list": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "properties": {
                        "example dict of multiple formats": {
                            "anyOf": [
                                {
                                    "properties": {
                                        "example list": {
                                            "type": "array",
                                            "minItems": 1,
                                            "maxItems": 10
                                        },
                                        "example number": {
                                            "type": "number"
                                        },
                                        "example value of any type": {
                                            "type": ["array", "string", "number", "boolean", "null"]
                                        }
                                    }
                                },
                                {
                                    "properties": {
                                        "example enum": {
                                            "type": "string",
                                            "enum": [
                                                "option 1",
                                                "option 2",
                                                "option 3"
                                            ]
                                        },
                                        "example string": {
                                            "type": "string"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
    }


def custom_schema_validation(instance: dict or bool, schema: dict) -> None:
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
            raise SchemaValidationError(f"Error validating {instance_str} because {err}{pattern_str}")
        else:
            raise SchemaValidationError(f"Error validating {instance_str}\n{err}")


def jsonify(jsondata: Any) -> Any:
    """
    Attempts to convert any non-json-compatible types into something analagous

    Args:
        jsondata (Any): object to convert

    Returns:
        Any: json-like object
    """
    if isinstance(jsondata, dict):
        for k, v in jsondata.items():
            jsondata[k] = jsonify(v)
    elif isinstance(jsondata, list):
        for i, e in enumerate(jsondata):
            jsondata[i] = jsonify(e)
    elif isinstance(jsondata, tuple):
        return jsonify(list(jsondata))
    else:
        if hasattr(jsondata, "to_json"):
            return jsonify(jsondata.to_json())
    return jsondata


def get_caller_name(layers=0):
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


def GetLogFormatter() -> logging.Formatter:
    class CustomFormatter(logging.Formatter):
        def custom_formatting_method(string):
            items = string.split("||")
            items = items[:2] + [get_caller_name(10)] +  items[2:]
            return " || ".join(items)

        def format(self, record):
            default_formatted = logging.Formatter.format(self, record)
            return CustomFormatter.custom_formatting_method(default_formatted)
    return CustomFormatter(f"%(asctime)s||%(levelname)5s||%(message)s")


def GetConsoleLogHandler() -> logging.StreamHandler:
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(GetLogFormatter())
    return consoleHandler


class TailLogHandler(logging.Handler):
    def __init__(self, log_queue):
        logging.Handler.__init__(self)
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.append(self.format(record))


class TailLogger(object):
    def __init__(self, maxlen):
        self._log_queue = collections.deque(maxlen=maxlen)
        self._log_handler = TailLogHandler(self._log_queue)

    def contents(self):
        return '\n'.join(self._log_queue)

    @property
    def log_handler(self):
        return self._log_handler


def generate_docs(d, file_str):
    os.system(f"python -m pdoc --html --output-dir {d} {file_str} --force")


def get_platform():
    return str(platform.system()).lower()


def resolve_ip(logger=None):
    import socket
    host = "proxy-chain.intel.com"
    port = 911
    try:
        s = socket.socket()
        s.settimeout(1)  # one second timeout so we don't hinder functionality
        try:
            s.connect(("intel.com", 80))  # website ip and port
            return s.getsockname()[0]
        except socket.timeout:
            s.connect((host, port))
        s.close()
    except socket.error as socket_error:
        try:
            s.close()
        except:
            # socket doesn't exist so we can't close it. this is not a problem though
            pass
        try:
            import subprocess
            if "linux" in get_platform():
                cmd = "hostname -i | awk '{print $1}'"
            else:
                cmd = "hostname -I | awk '{print $1}'"
            ip = subprocess.check_output(cmd.split(' ')).decode("utf-8").lower().strip()
            if ip.count('.') == 3:
                return ip
        except Exception as e:
            msg = f"Error during ip acquisition: {e}, after {socket_error}"
            write = logger.info if logger else print
            write(msg)
    # this may give us 127.0.0.1 on certain systems, or a virtualbox ip on others. neither are great but potentially functional
    return socket.gethostbyname(socket.gethostname())


if __name__ == "__main__":
    # generate_docs("docs/html", "aiohttp_server.py")
    print(get_platform())
    print("This file is not meant to be run directly, rather imported from")
