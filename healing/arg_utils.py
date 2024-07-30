import argparse
import logging
import os
import sys
from typing import Any, Sequence, Tuple


from definitions import ExitCodes, Strings
from log_utils import get_log
from utils import get_current_time_string_path_friendly, safe_path, str_to_log_level


class ArgNames:
    """
    Collection of arg names to be used by ArgOptions
    e.g. ArgOptions[ArgNames.config]
    """
    help = "help"
    log_level = "log_level"
    output = "output"  # output directory
    results = "results"  # syscheck results
    syscheck = "syscheck"  # how to rerun syscheck
    test_mode = "test_mode"
    version = "version"


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
    def __init__(self, long: str, short: str=None, alternative: str=None, default=None):
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
        self.default = default

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


class ArgOptions(dict):
    """
    Contains the grouping of argoption objects
    """
    def __init__(self):
        options = [
            ArgOption(ArgNames.help, 'h'),
            ArgOption(ArgNames.log_level, 'l', "log", default=logging.INFO),
            ArgOption(ArgNames.output, 'o', "output_dir", default=get_current_time_string_path_friendly()),
            ArgOption(ArgNames.results, 'r'),
            ArgOption(ArgNames.syscheck, 's', default=True),
            ArgOption(ArgNames.test_mode, default=False),
            ArgOption(ArgNames.version, 'v', "ver"),
        ]
        for option in options:
            setattr(self, option.long, option)  # set attribute so self.ip => ArgOption("ip"), etc.
            self[option.long] = option  # set dict reference so self["ip"] => ArgOption("ip"), etc.
    
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
    
    def print_args(self, to_log:bool=False, pretty:bool=False) -> None | dict | str:
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
    Class to provide custom arg helpers

    Create a class that inherits from this class, and override the __call__ function with your custom code
    """
    def __init__(self, option_strings, dest, default=False, required=False, help=None, nargs=0) -> None:
            super().__init__(option_strings=option_strings, dest=dest, const=True, default=default, required=required, help=help, nargs=nargs)


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
    
    def venv_dir(d: str) -> str:
        """
        determines if a directory is valid for a virtualenv dir

        Args:
            d (str): directory to check

        Raises:
            argparse.ArgumentTypeError: if it's not valid

        Returns:
            str: the directory in a safe form
        """
        new_d = safe_path(d, False)
        if os.path.exists(new_d):
            if os.access(os.path.dirname(new_d), os.W_OK):
                return new_d
            else:
                raise argparse.ArgumentTypeError(f"Virtualenv directory '{d}' is not a valid writeable path")
        else:
            root_d = os.path.split(new_d)[0]
            if root_d != new_d:
                if os.path.exists(root_d):
                    if os.access(os.path.dirname(root_d), os.W_OK):
                        return new_d
                    else:
                        raise argparse.ArgumentTypeError(f"Virtualenv directory '{d}' is not a valid writeable path")
                else:
                    return new_d
            else:
                return new_d

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
            raise argparse.ArgumentTypeError(f"Directory '{f}' is not a valid readable path")


STANDARD_PARSER = ArgumentParser(description="Self-Healing", parents=[], conflict_handler="resolve", add_help=False)
STANDARD_PARSER.add_argument(*ArgOptions.help, help="Help", action="store_true")  # store_true causes an arg to be readonly, no param needed
STANDARD_PARSER.add_argument(*ArgOptions.log_level, type=ArgHelperActions.log_level, help="Log level", default=ArgOptions.log_level.default)
STANDARD_PARSER.add_argument(*ArgOptions.output, type=ArgHelperActions.writeable_dir, help="Output directory", default=ArgOptions.output.default)
STANDARD_PARSER.add_argument(*ArgOptions.results, type=ArgHelperActions.readable_dir, help="Results")
STANDARD_PARSER.add_argument(*ArgOptions.version, help="Display version", action="store_true")  # store_true causes an arg to be readonly, no param needed


def _parse_args(parser:ArgumentParser, ignore_unknown:bool=True) -> Namespace:
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
        sys.exit(1)


def handle_base_args(args:Namespace):
    """
    Handles common/base/universal args

    Args:
        args (Namespace): args to handle
    """
    assert isinstance(args, Namespace), f"Need args to handle. Invalid object {type(args)} passed"
    if args.version:
        print(Strings.Version)
    if args.help:
        STANDARD_PARSER.epilog = "Contact brit.thornwell@intel.com for more help with this tool"
        STANDARD_PARSER.print_help()


def parse_and_handle_args(ignore_unknown:bool=True) -> Namespace:
    """
    Parses and handles args that were parsed if necessary

    Args:
        ignore_unknown (bool, optional): whether or not to ignore unknown arguments. Defaults to True.

    Returns:
        Namespace: the parsed args
    """
    args = _parse_args(STANDARD_PARSER, ignore_unknown=ignore_unknown)
    handle_base_args(args)
    return args


if __name__ == "__main__":
    from definitions import Strings
    print(Strings.NotStandalone)
