"""
This file contains utilities to manage arguments
"""

import argparse
import os
import sys
from typing import Any, Sequence, Tuple

from core.definitions import ExitCodes, Strings, TestDefaults, ConfigDefaultValues
from infra.file_utils import safe_path
from infra.log_utils import get_log, str_to_log_level


class ArgHelperActions:
    """
    Grouping of helper functions for parsers to leverage
    These can convert data, or simply check it's in good form
    """
    def log_level(l:str) -> int:
        """
        determines if the arg is a valid log level

        Args:
            l (str): the arg

        Raises:
            argparse.ArgumentTypeError: if it's not valid

        Returns:
            int: the logging log level equivalent
        """
        try:
            return str_to_log_level(l.upper())
        except Exception as not_log_level_exception:
            raise argparse.ArgumentTypeError(f"Log Level '{l}' is not a valid log level. Valid levels are: ERROR, WARN, INFO, DEBUG")

    def writeable_dir(d: str) -> str:
        """
        determines if a directory is valid

        Args:
            d (str): directory to check

        Raises:
            argparse.ArgumentTypeError: if it's not valid

        Returns:
            str: the directory in a safe form
        """
        new_d = safe_path(d.strip(), False)
        if os.access(os.path.dirname(new_d), os.W_OK):
            return new_d
        else:
            raise argparse.ArgumentTypeError(f"Directory '{d}' is not a valid writeable path")

    def readable_dir(d: str) -> str:
        """
        checks if a directory is readable

        Args:
            d (str): the directory to check

        Raises:
            argparse.ArgumentTypeError: if it's not valid

        Returns:
            str: the directory in a safe form
        """
        new_d = safe_path(d.strip(), False)
        if os.access(os.path.dirname(new_d), os.R_OK):
            return new_d
        else:
            raise argparse.ArgumentTypeError(f"Directory '{d}' is not a valid readable path")

    def readable_file(f: str) -> str:
        """
        Checks if a file is readable

        Args:
            f (str): the file path

        Raises:
            argparse.ArgumentTypeError: if it's not valid

        Returns:
            str: the file in a safe form
        """
        new_f = safe_path(f, False)
        if os.access(new_f, os.R_OK):
            return new_f
        else:
            raise argparse.ArgumentTypeError(f"File '{f}' is not a valid readable path")

    def valid_node(n: str, default=TestDefaults.NodeId) -> int:
        """
        Checks if a node id is valid

        Args:
            f (str): the node number

        Returns:
            int: the node in correct form
        """
        n = int(n)
        assert n >= 0, "Node value should be 0 or higher"
        assert n <= 10_000, "Node value should be something reasonable to use in a cluster (currently less than 10 thousand)"
        return n

    def valid_duration(d: str) -> int:
        """
        Checks if a duration is valid
        Using seconds for duration

        Args:
            d (str): the duration number

        Returns:
            int: the duration in correct form
        """
        d = int(d)
        assert d > 0, "Duration value should be higher than 0"
        # 60 seconds -> minute
        # 3600 seconds -> hour
        # 3600 * 24 -> day
        assert d <= 10_000, "Duration value should be something reasonable to use (currently less than 10 thousand)"
        return d

    def valid_seed(s: str | int) -> int:
        """
        Checks if a seed is valid
        """
        s = int(s)
        assert s >= 0, "Seed value should be 0 or higher"
        assert s <= 1_000_000_000, "Seed value should be something reasonable to use (currently less than 1 billion)"
        return s

    def valid_dev_cnt(d: str) -> int:
        """
        Checks if a device count is valid

        Args:
            d (str): the device count

        Returns:
            int: the device count in correct form
        """
        d = int(d)
        assert d > 0, "device count value should be higher than 0"
        print(d)
        return d

    def valid_ip(ip: str) -> str:
        """
        Checks if an IP address is valid

        Args:
            ip (str): the ip address

        Raises:
            argparse.ArgumentTypeError: if it's not valid

        Returns:
            str: the ip
        """
        from ipaddress import ip_address
        try:
            ip_address(ip)
            return ip
        except Exception as ip_exception:
            raise argparse.ArgumentTypeError(f"Node IP address '{ip}' is not a valid IP address") from ip_exception


class ArgOption:
    """
    Contains a grouping of argparse options
    options include 
    self.long -> long_name
    self.short -> short_name
    self.alternative -> alternative_name
    self.base_args -> [long_name, short_name, alternative_name]
    self.args -> [--long_name, -short_name, --alternative_name]
    """
    def __init__(self, long: str, short: str=None, alternative: str=None, type=None, default=None, nargs='?', help_str :str=None, action :str="store"):
        self.long = long.strip('-')
        self.short = short.strip('-') if short else short
        self.alternative = alternative.strip('-') if alternative else alternative
        self.base_args = [o for o in [self.long, self.alternative, self.short] if o is not None]
        arg_len = len(self.base_args)
        set_len = len(set(self.base_args))
        assert arg_len == set_len, f"Argument options contains {arg_len-set_len} duplicate(s) in '{self.base_args}'"
        self.args = [f"--{self.long}"]
        if self.short:
            self.args.append(f"-{self.short}")
        if alternative:
            self.args.append(f"--{self.alternative}")
        self.type = type
        self.default = default
        assert help_str, f"Someone forgot to provide a help string for the --{self.long} parameter!"
        self.help = help_str
        if self.default:
            self.help += f". Default is {self.default}"
        self.action = action
        self.nargs = nargs

    def get_options(self) -> Sequence[str]:
        """
        returns the options in a friendly way

        Returns:
            Sequence[str]: the list of options
        """
        return self.base_args

    def __iter__(self):
        return (i for i in self.args)  # return the members that are not empty
    
    def __str__(self):
        return f"{self.long}: --{self.long}, -{self.short} or --{self.alternative}"


################################################################
# Define arguments to be used by the parser here in ArgOptions #
################################################################

class ArgOptions(dict):
    """
    Contains the grouping of argoption objects
    """
    def __init__(self):
        self.options = [
            ArgOption("all", 'a', help_str="Run all tests"),  # run all tests - doesn't require a config to run
            ArgOption("check", help_str="Check the configuration file"),  # check the configuration file for errors
            ArgOption("config", 'c', nargs='+', type=ArgHelperActions.readable_file, help_str="Specify the configuration file(s) to use"),  # config file to use for generating a schedule or running
            ArgOption("duration", 'd', type=ArgHelperActions.valid_duration, default=ConfigDefaultValues.Duration, help_str="Set the minimum duration for the test"),  # set the minimum duration for the test
            ArgOption("exclude", 'e', "ex", nargs='+', help_str="Exclude specific workloads"),  # exclude specific workloads from running
            ArgOption("help", 'h', help_str="Show this help message"),
            ArgOption("info", 'i', help_str="Show the system information"),  # show the system information
            ArgOption("list", 'l', help_str="List available configurations and workloads", action="store_true"),  # list available configurations and workloads
            ArgOption("log", 'L', "loglevel", type=ArgHelperActions.log_level, default="INFO", help_str="Set the log level"),  # set the log level for logging
            ArgOption("out", 'o', "output", type=ArgHelperActions.writeable_dir, help_str="Set the output directory"),  # change the output directory for logs and workload results
            ArgOption("profile", 'p', help_str="Profile the tests"),  # profile the tests to see where time is spent
            ArgOption("run", 'r', help_str="Run a config or schedule", type=ArgHelperActions.readable_file),  # run a config or schedule
            ArgOption("schedule", 's', help_str="Create a schedule", action="store_true"),  # create a schedule for the tests, using a config
            ArgOption("seed", 'S', help_str="set the seed to use for reproducibility", default=ConfigDefaultValues.Seed),  # set the seed to use in the schedule, config, or for the workload to run
            ArgOption("timeout", 't', "to", type=int, default=ConfigDefaultValues.Timeout, help_str="Set a timeout for the test"),  # set a timeout for the schedule/config/workload
            ArgOption("verbose", 'v', help_str="Enable verbose mode"),  # enable verbose mode for more logging
            ArgOption("workload", 'w', "wl", help_str="Run a specific test"),  # run a specific workload
            ArgOption("test", help_str="Run in test mode"),  # enable test mode which disables some checks - need to clearly define this mode
            ArgOption("version", 'v', help_str="Show the version info"),
            ArgOption("listen", 'x', alternative="execute", help_str="Enter listen/execute mode", action="store_true"),  # enter listen/execute mode
        ]
        for option in self.options:
            setattr(self, option.long, option)  # set attribute so self.config => ArgOption("config"), etc.
            self[option.long] = option  # set dict reference so self["config"] => ArgOption("config"), etc.
    
    def list_option_names(self, display:bool=False) -> Sequence[str]:
        """
        lists all available options

        Args:
            display (bool, optional): whether or not to print the list. Defaults to False.

        Returns:
            Sequence[str]: the list of option strings
        """
        if display:
            print('\n'.join(self.keys()))
        return list(self.keys())
    
    def items(self) -> dict:
        """
        returns a dict with arg option names and their default values (for when no args are passed)

        Returns:
            dict[str, Any]: dict of arg options and their defaults
        """
        items = super().items()
        to_return = dict()
        for k, v in items:
            to_return[k] = v.default
        return to_return


ArgOptions = ArgOptions()


class Namespace():
    """
    This is a wrapper around the argparse Namespace that allows args to be looked up easier
    """
    def __init__(self, instance: argparse.Namespace) -> None:
        self.__class__ = type(instance.__class__.__name__,
                              (self.__class__, instance.__class__),
                              {})
        self.__dict__ = instance.__dict__
    
    def merge(self, instance: argparse.Namespace):
        """
        merges two Namespace objects, used when adding manager parsers to the service parser

        Args:
            instance (argparse.Namespace): the namespace to add to this instance

        Returns:
            Namespace: this instance merged with the other on top
        """
        self.__dict__.update(instance.__dict__)
        return self

    def __getitem__(self, item):
        return getattr(self, item)
    
    def keys(self) -> Sequence[str]:
        """
        returns the keys in a list

        Returns:
            Sequence[str]: the keys
        """
        return self.__dict__.keys()
    
    def values(self) -> Sequence[Any]:
        """
        returns the values in a list

        Returns:
            Sequence[Any]: the values
        """
        return self.__dict__.values()

    def items(self) -> Sequence[Tuple[str, Any]]:
        """
        returns the items as key value pairs

        Returns:
            _type_: the ley value pairs
        """
        return self.__dict__.items()
    
    def print_args(self, to_log:bool=False, pretty:bool=False) -> dict:
        """
        Prints or returns a structure containing the arguments and their values

        Args:
            to_log (bool, optional): whether or not to print to the log instead of returning the dict. Defaults to False.
            pretty (bool, optional): Whether or not to format nicer than a dictionary, will return a string. Defaults to False.

        Returns:
            None or str or dict: None if to_log, str if pretty, otherwise a dict
        """
        args = vars(self)
        if pretty:
            pretty_args = ""
            longest_key = 0
            longest_val = 0
            for key, val in args.items():
                longest_key = max(longest_key, len(key))
                longest_val = max(longest_val, len(str(val)))
            for key, val in args.items():
                pretty_args += f"\n{key.ljust(longest_key)} | {str(val).ljust(longest_val)}"
            header = f"{'Name'.ljust(longest_key)} | {'Value'.ljust(longest_val)}"
            args = f"{header}\n{'-'*len(header)}{pretty_args}"
        if to_log:
            get_log().info(str(args))
        else:
            return args


class ArgumentParser(argparse.ArgumentParser):
    """
    Override class to properly handle errors
    """
    def __init__(self, *args, **kwargs) -> None:
        if kwargs.get("parents", None) is None or not kwargs.get("conflict_handler", None):
            raise Exception("ArgumentParsers should have 'parents' and 'conflict_handler' in the argument list")
        super().__init__(*args, **kwargs)


    def error(self, message):
        """
        error handler, overrides the fatal exit

        Args:
            message (str): error message

        Raises:
            Exception: failure to parse
        """
        raise Exception(message)
    
    def add_argument(self, *name_or_flags:Any, **kwargs: Any) -> argparse.Action:
        """
        adds an arg to be able to be parsed
        """
        try:
            return super().add_argument(*name_or_flags, **kwargs)
        except TypeError as type_exception:
            if "'ArgOption' object is not subscriptable" in f"{type_exception}":
                try:
                    e_info = sys.exc_info()[2].tb_next.tb_frame.f_back.f_back
                    file_name = e_info.f_code.co_filename
                    line = e_info.f_lineno
                except:
                    raise Exception(f"It appears you entered parser.add_argument(ArgOptions.<option> but you need to unpack the ArgOption e.g. *ArgOptions.<option> instead of ArgOptions.<option>") from type_exception
                raise Exception(f"It appears you entered parser.add_argument(ArgOptions.<option> on line {line} of {os.path.relpath(file_name)} but you need to unpack the ArgOption e.g. *ArgOptions.<option> instead of ArgOptions.<option>") from type_exception
            else:
                raise type_exception


class CustomArgHelperAction(argparse.Action):
    """
    Base class to provide custom arg helpers

    Create a class that inherits from this class, and override the __call__ function with your custom code
    """
    def __init__(self, option_strings, dest, default=False, required=False, help=None, nargs=0) -> None:
            super().__init__(option_strings=option_strings, dest=dest, const=True, default=default, required=required, help=help, nargs=nargs)


PARSER = ArgumentParser(description="PSE SVCE Content XA-Scale", parents=[], conflict_handler="resolve", add_help=False)
for option in ArgOptions.options:
    if option.type:  # type and default don't play well together, so we need to omit type if possible
        PARSER.add_argument(*option, type=option.type, default=option.default, help=option.help, action=option.action)
    else:
        PARSER.add_argument(*option, default=option.default, help=option.help, action=option.action)


def parse_args(parser:ArgumentParser=PARSER, ignore_unknown:bool=True) -> Namespace:
    """
    Attempts to parse args with the provided argparser
    will show help on failure
    by default will ignore unknown arguments

    Args:
        parser (ArgumentParser): the parser to use
        ignore_unknown (bool, optional): Whether or not to skip over broken/unknown arguments. Defaults to True.

    Raises:
        parse_exception: Issue parsing args
    
    Returns:
        Namespace: subscriptable wrapper around argparse namespace to get arg values
    """
    try:
        parsed = parser.parse_args()
        return Namespace(parsed)
    except Exception as parse_exception:
        exc_str = f"{parse_exception}"
        print(exc_str)
        if exc_str.startswith("unrecognized argument"):
            broken_args = [arg for arg in exc_str.split(' ') if arg.startswith('-')]
        else:
            # not sure what we can do here yet
            raise parse_exception
        all_opts = []
        for v in ArgOptions.values():
            all_opts.extend([*v])
        for broken in broken_args:
            from difflib import get_close_matches
            matches = get_close_matches(broken, all_opts)
            if len(matches):
                print(f"Instead of '{broken}', did you mean {matches}?")
        parser.print_help()
        if ignore_unknown:
            parsed, _ = parser.parse_known_args()
            return Namespace(parsed) # parses only args that are known, i.e. will ignore missing/broken args
        else:
            raise parse_exception
    except SystemExit:
        # inner = argparse.Namespace(**ArgOptions.items())
        # return Namespace(inner)
        import sys
        sys.exit(ExitCodes.Err)


def print_help():
    """
    Prints the help message
    """
    PARSER.epilog = f"Contact {Strings.Contact} for more help with this tool"
    PARSER.print_help()
    exit(ExitCodes.Okay)


def print_version():
    """
    Prints the version
    """
    print(Strings.Version)


if __name__ == "__main__":
    print(Strings.NotStandalone)
