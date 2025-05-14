"""
This file is used to manage files and directories
"""

import json
import jsonschema
import os
from pathlib import Path
import re
from types import ModuleType
from typing import Any

from core.definitions import Directories, RegexStrings


_proj_root = None
_proj_root_str = None


def get_project_root(as_str=False) -> Path:
    """
    returns the root of the project by getting this file (located in root/) and then going one directory up

    Args:
        as_str (bool, optional): whether or not to return the path as a string instead of a path object. Defaults to False.

    Returns:
        Path: the path to the root of the project
    """
    global _proj_root
    global _proj_root_str
    if not _proj_root:
        root = os.path.dirname(os.path.abspath(__file__))
        _proj_root = Path(root).resolve()
        _proj_root_str = root
    return _proj_root_str if as_str else _proj_root


def get_output_root(directory=None) -> Path:
    if os.path.exists(Directories.ContainerSharedDir):
        # running containerized build
        return os.path.join(Directories.ContainerSharedDir, directory) if directory else Directories.ContainerSharedDir
    else:
        return os.path.join(get_project_root(), directory) if directory else get_project_root()


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


def sanitize_dict(instance: dict) -> bool:
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
    mod_path: Path = safe_path(mod_path, relative=relative)
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


def load_json_file_2_dict(json_file: str, comment_remove: bool=True, expand_path: bool=True, fix: bool=True, log=None) -> dict:
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


def load_json(to_load: str) -> dict:
    """
    Loads json data either by loading the file from the given path if to_load is a string, or directly loads it from
    to_load it is a dictionary it returns to_load. Performs a sanitization check the json once it has been
    loaded.
    Args:
        to_load (str | dict | Path): either the json itself to load or the path to load the json file from

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


def load_data(to_load: str) -> dict:
    """
    Attemps to load data from whatever format given, generally a dict/json, but could be a python module

    Args:
        to_load (str | dict | Path): the data to load

    Returns:
        dict: the formatted data
    """
    file = to_load if to_load is Path else safe_path(to_load, relative=False)
    if file.name.endswith(".py") and not "__init__" in file.name:
        result = import_module_from_path(file, relative=False)
    else:
        result = load_json(file)
    return result


def save_json(data, file: str | Path):
    """
    Save a json file
    """
    if isinstance(file, Path) or isinstance(file, str):
        with open(file, "w") as f:
            json.dumps(str(data), f)
    else:
        try:
            json.dumps(str(data), file)
        except Exception as e:
            raise Exception(f"Failed to save json data to file, is 'file' a file pointer or different object?: {e}") from e


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
        else:
            return jsondata
    return jsondata


def compress_json(data:dict) -> bytes:
    """
    Converts a json object/dict to utf-8 bytes and then compresses with gzip (default compression)
    The data should be sanitary and actual json so use jsonify and sanitize_json first!

    Args:
        data (dict): the json obj to compress

    Returns:
        bytes: the compressed utf-8 byte string
    """
    import zlib
    if isinstance(data, dict) or isinstance(data, list):
        data = json.dumps(data)
    else:
        assert isinstance(data, str), "Json data is not in the correct form!"
    return zlib.compress(data.encode('utf-8'))


def validate_with_schema(instance: dict, schema: dict, source_name: str =None) -> None:
    """
    Wraps the jsonschma's validate function with some better error handling, especially useful in the case of custom error messages

    Args:
        instance (dict or bool): a json-like object to validate, generally a dict
        schema (dict): the schema to use to validate the instance
        source_name (str): the name of the source data

    Raises:
        SchemaValidationError: error validating the schema
    """
    try:
        jsonschema.validate(instance, schema)
        return instance
    except Exception as validation_exception:
        err = f"{validation_exception}"
        instance_str = f"{instance}"
        if len(instance_str) > 32:  # need to shrink this down
            instance_str = f"{instance_str[:32]}..."
        err_msg = f"Error validating {instance_str} "
        if source_name:
            err_msg += f"from {source_name} "
        errs = err.split("\n\n")
        try:
            err_msg += "because " + errs[0] + ' ' + errs[2]
        except IndexError:
            if "error message" in err:
                err_msg = errs[0]
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
                err_msg += f"because {err}{pattern_str}"
            else:
                err_msg += f"\n{err}"
                raise jsonschema.ValidationError(err_msg)
        raise jsonschema.ValidationError(err_msg)
        