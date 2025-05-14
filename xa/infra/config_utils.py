"""
This file contains utilities to manage configurations
"""


import copy
from pathlib import Path
from infra.data.config_schema import schema
from infra.file_utils import load_data, validate_with_schema
from core.definitions import ConfigKeys, ConfigMandatoryKeys, Strings


def load_config(config: str | Path, check: bool = True) -> dict:
    """
    Load a configuration file
    """
    if isinstance(config, dict):
        return config  # already loaded
    elif isinstance(config, Path):
        config = str(config)
    if isinstance(config, str):
        path = config
        config = load_data(config)
        if path.endswith(".json"):  # should be json
            pass            
        elif path.endswith(".py"):  # should be python
            config = config.config
        else:
            raise ValueError(f"Invalid configuration file: {path}")
        config[ConfigKeys.File] = path
    else:
        raise ValueError(f"Invalid configuration file: '{config}'")
    if check:
        assert check_config(config), "Invalid configuration, cannot continue!"
    return config


def check_config(config: dict) -> bool:
    """
    Check if the configuration is valid
    do syntax check, and then need to connect to parameters checks
    """
    # assert that the mandatory keys are present in the config
    assert isinstance(config, dict) and len(config), "No data present in provided config"
    config_id = config.get(ConfigKeys.Name, config.get(ConfigKeys.File, None))
    # check for correct data types
    assert validate_with_schema(config, schema, config_id)
    return True


def merge_config(base_cfg: dict, new_cfg: dict, view_overridden:bool=False) -> dict:
    """
    Merge two dictionaries with the custom data overriding the default data if the key exists in both
    :param default_data: (dict) old data to merge on top of
    :param custom_data: (dict) new data to merge
    :param view_overridden: whether or not to get a list of overridden values as well
    :return: (dict or dict,list) merged dict [optionally with list of overridden keys]
    """
    def merge_json_internal(dest_data, new_data, view_overrides, overrides):
        if new_data:
            for key in new_data:
                if key in dest_data:
                    if isinstance(dest_data[key], dict) and isinstance(new_data[key], dict):
                        if view_overrides:
                            overrides.append(key)
                        merge_json_internal(dest_data[key], new_data[key], view_overrides, overrides)
                    elif isinstance(dest_data[key], dict) and isinstance(new_data[key], dict) and key == "codestreams":  # TODO are there others to merge to?
                        if view_overrides:
                            overrides.append(key)
                        dest_data[key].extend(new_data[key])
                    elif any([isinstance(data[key], dict) for data in [dest_data, new_data]]) and any([isinstance(data[key], list) for data in [dest_data, new_data]]):
                        msg = f"During merge, destination json's {key} section is a {type(dest_data[key])} and the override data is {type(new_data[key])}. These are not compatible"
                        raise Exception(msg)
                    else:
                        if view_overrides:
                            overrides.append(key)
                        dest_data[key] = copy.deepcopy(new_data[key])
                else:
                    dest_data.update({key: copy.deepcopy(new_data[key])})
        return dest_data
    if view_overridden:
        overridden = []
        return merge_json_internal(copy.deepcopy(base_cfg), new_cfg, True, overridden), overridden
    else:
        return merge_json_internal(copy.deepcopy(base_cfg), new_cfg, False, None)

def merge_json_dict(base_cfg, new_cfg, view_overridden:bool=False):
    """
    Merge two dictionaries with the custom data overriding the default data if the key exists in both
    :param default_data: (dict) old data to merge on top of
    :param custom_data: (dict) new data to merge
    :param view_overridden: whether or not to get a list of overridden values as well
    :return: (dict or dict,list) merged dict [optionally with list of overridden keys]
    """
    def merge_json_internal(dest_data, new_data, view_overrides, overrides):
        if new_data:
            for key in new_data:
                if key in dest_data:
                    if isinstance(dest_data[key], dict) and isinstance(new_data[key], dict):
                        if view_overrides:
                            overrides.append(key)
                        merge_json_internal(dest_data[key], new_data[key], view_overrides, overrides)
                    elif isinstance(dest_data[key], dict) and isinstance(new_data[key], dict) and key == "codestreams":  # TODO are there others to merge to?
                        if view_overrides:
                            overrides.append(key)
                        dest_data[key].extend(new_data[key])
                    elif any([isinstance(data[key], dict) for data in [dest_data, new_data]]) and any([isinstance(data[key], list) for data in [dest_data, new_data]]):
                        msg = f"During merge, destination json's {key} section is a {type(dest_data[key])} and the override data is {type(new_data[key])}. These are not compatible"
                        raise Exception(msg)
                    else:
                        if view_overrides:
                            overrides.append(key)
                        dest_data[key] = copy.deepcopy(new_data[key])
                else:
                    dest_data.update({key: copy.deepcopy(new_data[key])})
        return dest_data
    if view_overridden:
        overridden = []
        return merge_json_internal(copy.deepcopy(base_cfg), new_cfg, True, overridden), overridden
    else:
        return merge_json_internal(copy.deepcopy(base_cfg), new_cfg, False, None)


if __name__ == "__main__":
    print(Strings.NotStandalone)
