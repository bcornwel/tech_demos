from io import UnsupportedOperation
import re
import sys
import json
import time
import inspect
import functools
import logging
from typing import Any, Callable
import jsonschema
import async_networking
import asyncio


logging.basicConfig(filename="test2.log", level=logging.INFO)
logger = logging.getLogger('agnostic')
logger.info("agnostic event handling")
asyncio.run(async_networking.tasks().run())

class SchemaValidationError(Exception):
    pass


class NonExistantFunction(Exception):
    pass


class GlobalTriggers:
    FunctionPrinting = True
    Timing = True


class Const:
    class Event:
        Event_ID = "event_id"
        Message = "message"
        Targets = "targets"
        Data = "data"
        Addr = "addr"
        Params = "params"
        Value = "value"
        Type = "type"
        Module = "module"
        Source = "source"
        Primitive = "primitive"
        Function = "function"
        Class = "class"
    class Engine:
        Generic = "generic"
        DefaultIP = "127.0.0.1"
        DefaultPort = 6277  # m a r s 
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
    class Generic:
        NA = "N/A"

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


class Schemas:
    Event = {
        "type": "object",
        "properties": {
            Const.Event.Event_ID: {
                "type": "string",
                "pattern": Const.Regex.Job_ID,
                "error message": "event_id should be of the form seed_p_t_d_datetime e.g. 000000_0_0_0_00000000"
            },
            Const.Event.Source: {
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
            Const.Event.Message: {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "prefixItems": [
                    {
                        "type": "string"
                    },
                    {
                        "type": "string"
                    }
                ],
                "items": False
            },
            Const.Event.Targets: {
                "type": "array",
                "minItems": 1,
                "items": {
                    "properties": {
                        Const.Event.Addr: {
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
                            ],
                            "items": False
                        },
                        Const.Event.Data: {
                            "anyOf": [
                                {
                                    "properties": {
                                        Const.Event.Type: {
                                            "type": "string",
                                            "enum": [
                                                Const.Event.Primitive,
                                                Const.Event.Function,
                                                Const.Event.Class
                                            ]
                                        },
                                        Const.Event.Value: {
                                            "type": "string"
                                        },
                                        Const.Event.Params: {
                                            "type": ["array", "string", "number", "boolean", "null"]
                                        },
                                        Const.Event.Module: {
                                            "type": "string"
                                        }
                                    }
                                },
                                {
                                    "properties": {
                                        Const.Event.Type: {
                                            "type": "string",
                                            "enum": [
                                                Const.Event.Primitive,
                                                Const.Event.Function,
                                                Const.Event.Class
                                            ]
                                        },
                                        Const.Event.Value: {
                                            "type": "string"
                                        },
                                        Const.Event.Params: {
                                            "type": ["array", "string", "number", "boolean", "null"]
                                        }
                                    }
                                },
                                {
                                    "properties": {
                                        Const.Event.Type: {
                                            "type": "string",
                                            "enum": [
                                                Const.Event.Primitive,
                                                Const.Event.Function,
                                                Const.Event.Class
                                            ]
                                        },
                                        Const.Event.Value: {
                                            "type": "string"
                                        },
                                        Const.Event.Module: {
                                            "type": "string"
                                        }
                                    }
                                },
                                {
                                    "properties": {
                                        Const.Event.Type: {
                                            "type": "string",
                                            "enum": [
                                                Const.Event.Primitive,
                                                Const.Event.Function,
                                                Const.Event.Class
                                            ]
                                        },
                                        Const.Event.Value: {
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


FlowRegistry = {}
 
def register_step(name: str) -> Callable:
    """
    Registers a 'test' step in the FlowRegistry dict

    Args:
        name (string): step name
    Returns the wrapped function
    """
    def register(func):
        FlowRegistry[name] = func
        return func
    return register


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
        if GlobalTriggers.FunctionPrinting:
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
        if GlobalTriggers.Timing:
            start_time = time.perf_counter()
        ret = func(*args, **kwargs)
        if GlobalTriggers.Timing:
            end_time = time.perf_counter()
            run_time = end_time - start_time
            print(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        if GlobalTriggers.FunctionPrinting:
            print(f"Done r{msg[1:]}")
        return ret

    return wrapper


def decorate_all_methods(decorator: Callable) -> Callable:
    """
    Decorates all the methods in a class (includes static methods)

    Args:
        decorator (function): the decorator to apply to the methods
    """
    def decorate(cls):
        for attr in cls.__dict__:
            gattr = getattr(cls, attr)
            if callable(gattr):
                setattr(cls, attr, decorator(gattr))
        return cls
    return decorate


@debug_decorator
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
            instance_type = f"{type(instance)}"
            if Const.Event.Class in instance_type:
                instance_str = instance_type
            else:
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
        return list(jsondata)
    # else:
    #     do any other processing here
    return jsondata


@debug_decorator
@register_step("1")
def example_step1():
    print("This is an example step")


@debug_decorator
@register_step("2")
def example_step2():
    print("This is the second example step")


@debug_decorator
@register_step("3")
def example_step3():
    print("This is the third example step")


SpecificEventMap = {
    "example_step1": example_step1,
    "example_step2": example_step2,
    "example_step3": example_step3,
    "test function 3": print
}


class TestClass:
    def __init__(self, name="Test class", message="Test message"):
        self.name = name
        self.message = message

    def __str__(self):
        return f"{self.name}: {self.message}"


class EngineHandle():
    def __init__(self, addr: tuple or str, port: int = None):
        if port is None:
            if isinstance(addr, list):
                port = addr[1]
                addr = addr[0]
            else:
                port = Const.Engine.DefaultPort
        assert isinstance(port, int) and 1024 < port < 65_535
        self.port = port
        self.addr = addr
    
    def __eq__(self, other) -> bool:
        if isinstance(other, EngineHandle):
            return self.addr == other.addr and self.port == other.port
        elif isinstance(other, tuple):
            return (self.addr,self.port) == other
        elif isinstance(other, list):
            return [self.addr,self.port] == other
        else:
            raise UnsupportedOperation("EngineHandle __eq__ parameter is not a known form of EngineHandle")
    
    def __hash__(self) -> int:
        return hash((self.addr, self.port))


class Event(dict):
    def __init__(self, **kwargs):
        self.update(jsonify(kwargs))
        custom_schema_validation(self, Schemas.Event)
        # jsonschema.validate(self, Schemas.Event)
        RegexValidator().validate(self)
    
    def __str__(self) -> str:
        return f"Event {self.get(Const.Event.Event_ID, Const.Generic.NA)} '{self.get(Const.Event.Message, [Const.Generic.NA])[0]}'"


@decorate_all_methods(debug_decorator)
class Engine:
    def __init__(self, name: str = None, addr: str = None, port: int = None, peers: list = None, event_mapping: dict = None):
        self.name = name if name else Const.Engine.Generic
        self.handle = EngineHandle(addr if addr else Engine.resolve_ip(), port if port else Const.Engine.DefaultPort)
        self.peers = dict()
        self.add_peers(peers)
        self.event_map = event_mapping if event_mapping else {"test function 3": print}  # this is the agnostic functionality for running functions based on messages

    def add_peers(self, peers: list or tuple or None) -> None:
        """
        Adds peers to the engine's 'database'

        Args:
            peers (list or tuple or None): the peer(s) to add
        """
        if peers is not None:
            if isinstance(peers, tuple):
                peers = {peers[0]: peers[1]}
            for addr, engine in peers.items():
                self.peers[addr] = engine  # TODO: this would change in a real scenario with the engine address being the only pertinent/available info

    def handle_event(self, event: Event) -> bool:
        """
        Handles an event, whether that means running a function, using a custom event handler, or forwarding the event

        Args:
            event (Event): The event to handle

        Raises:
            NonExistantFunction: If the function cannot be called

        Returns:
            bool: whether or not the event was handled
        """
        handled = False
        for target in event[Const.Event.Targets]:
            if EngineHandle(target[Const.Event.Addr]) == self.handle:
                if target[Const.Event.Data][Const.Event.Type] == Const.Event.Function:
                    print(f"Handling event '{event[Const.Event.Event_ID]}' '{event[Const.Event.Message][0]}' function")
                    try:
                        funcs = [getattr(self, func) for func in dir(self) if func == target[Const.Event.Data][Const.Event.Value] and callable(getattr(self, func))]
                        if not len(funcs):
                            try:
                                if Const.Event.Module in target[Const.Event.Data]:
                                    import importlib
                                    mod = importlib.import_module(target[Const.Event.Data][Const.Event.Module])
                                else:
                                    mod = sys.modules[__name__]
                                func = getattr(mod, target[Const.Event.Data][Const.Event.Value])
                            except Exception as class_exception:
                                print(f"Unable to create class {target[Const.Event.Data][Const.Event.Value]}: {class_exception}")
                            raise NonExistantFunction(f"Function '{target[Const.Event.Data][Const.Event.Value]}' does not exist")
                        elif len(funcs) > 1:
                            raise NonExistantFunction(f"Somehow there are more than one '{target[Const.Event.Data][Const.Event.Value]}' in {self.name}")
                        else:
                            func = funcs[0]
                        if Const.Event.Params in target[Const.Event.Data]:
                            func(*target[Const.Event.Data][Const.Event.Params])
                        else:
                            func()
                        handled = True
                    except Exception as dynamic_function_exception:
                        print(f"Unable to run function '{target[Const.Event.Data][Const.Event.Value]}': '{dynamic_function_exception}'")
                else:
                    if target[Const.Event.Data][Const.Event.Type] == Const.Event.Primitive:
                        data = target[Const.Event.Data][Const.Event.Value]
                    elif target[Const.Event.Data][Const.Event.Type] == Const.Event.Class:
                        try:
                            if Const.Event.Module in target[Const.Event.Data]:
                                import importlib
                                mod = importlib.import_module(target[Const.Event.Data][Const.Event.Module])
                            else:
                                mod = sys.modules[__name__]
                            class_ = getattr(mod, target[Const.Event.Data][Const.Event.Value])
                            data = class_(*target[Const.Event.Data][Const.Event.Params])
                        except Exception as class_exception:
                            print(f"Unable to create class {target[Const.Event.Data][Const.Event.Value]}: {class_exception}")
                    assert event[Const.Event.Message][0] in self.event_map, f"Could not find event mapping for {event[Const.Event.Message][0]} in {self.name}"
                    self.event_map[event[Const.Event.Message][0]](data)
                    handled = True
            else:
                self.forward_to_peer(event)
        if not handled:
            print("Did not handle")    
        return handled

    def example_function(self, *args) -> None:
        print(args)

    def example_flow(self) -> None:
        """
        Runs the items in the FlowRegistry dict
        """
        for k, v in sorted(FlowRegistry.items()):
            print(f"Result of {k} is {v()}")

    def breakpoint(self):
        breakpoint()

    def forward_to_peer(self, event: Event) -> bool:
        """
        Forwards events to other engines
        TODO: this should have the actual networking code here to send events

        Args:
            event (Event): Event to forward

        Returns:
            bool: whether or not the event was forwarded
        """
        sent = False
        for i, d in enumerate(event[Const.Event.Targets]):
            if d['addr'] == [self.handle.addr, self.handle.port]:
                event[Const.Event.Targets].pop(i)  # TODO: this should be better. Perhaps creating a new event with external targets only
                break
        if len(event[Const.Event.Targets]):
            for target in event[Const.Event.Targets]:
                handle = EngineHandle(target[Const.Event.Addr])
                if handle in self.peers:
                    sent = True
                    self.peers[handle].handle_event(event)
            print(f"{'Unable to forward' if sent else 'Successfully forwarded'} event {event[Const.Event.Message][0]}")
        return sent

    @staticmethod
    def resolve_ip() -> str:
        """
        Placeholder function for resolving the engine's external ip address

        Returns:
            str: _description_
        """
        return Const.Engine.DefaultIP


if __name__ == "__main__":
    engine_1_addr = (Engine.resolve_ip(), Const.Engine.DefaultPort)
    engine_2_addr = (Const.Engine.DefaultIP, Const.Engine.DefaultPort+1)
    test_engine_1 = Engine("Test Engine 1", engine_1_addr[0], engine_1_addr[1], event_mapping=SpecificEventMap)
    test_engine_2 = Engine("Test Engine 2", engine_2_addr[0], engine_2_addr[1], peers={engine_1_addr: test_engine_1}, event_mapping=SpecificEventMap)
    test_engine_1.add_peers({engine_2_addr: test_engine_2})
    print("Created engine")

    test_event = Event(event_id="000001_0_0_0_12345678", message=("test function", "high"), source=engine_2_addr, targets=[{Const.Event.Addr: engine_1_addr, Const.Event.Data: {Const.Event.Type: Const.Event.Function, Const.Event.Value: "example_function", Const.Event.Params: ["This is a test message", "This is another test message"]}}])
    print("Created event:", test_event)

    test_engine_1.handle_event(test_event)

    test_event_2 = Event(event_id="000002_0_0_0_12345678", message=("test function 2", "high"), source=engine_1_addr, 
                         targets=[
                            {Const.Event.Addr: engine_1_addr, Const.Event.Data: {Const.Event.Type: Const.Event.Function, Const.Event.Value: "example_function", Const.Event.Params: [f"This is a forwarded test message", "This is another forwarded test message"]}},
                            {Const.Event.Addr: engine_2_addr, Const.Event.Data: {Const.Event.Type: Const.Event.Function, Const.Event.Value: "example_function", Const.Event.Params: "This is a non-fwd test message"}}
                            ])
    test_engine_2.handle_event(test_event_2)

    test_event_3 = Event(event_id="000003_0_0_0_12345678", message=("test function 3", "high"), source=engine_2_addr, 
                         targets=[
                            {Const.Event.Addr: engine_1_addr, Const.Event.Data: {Const.Event.Type: Const.Event.Class, Const.Event.Value: TestClass.__name__, Const.Event.Params: ["custom name", "custom message"]}},
                            ])
    test_engine_1.handle_event(test_event_3)

    test_event_4 = Event(event_id="000004_0_0_0_12345678", message=("test function 4", "high"), source=engine_2_addr, 
                         targets=[
                            {Const.Event.Addr: engine_1_addr, Const.Event.Data: {Const.Event.Type: Const.Event.Function, Const.Event.Value: "example_flow"}},
                            ])
    test_engine_1.handle_event(test_event_4)

    test_event_5 = Event(event_id="000005_0_0_0_12345678", message=("test function 5", "high"), source=engine_2_addr, 
                         targets=[
                            {Const.Event.Addr: engine_1_addr, Const.Event.Data: {Const.Event.Type: Const.Event.Function, Const.Event.Value: "breakpoint"}},
                            ])
    test_engine_1.handle_event(test_event_5)
    
    print("Finished processing events")
