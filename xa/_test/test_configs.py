"""
This file should contain functions to test the config loading, reading, saving, merging, etc functions
It should also verify that the current configs are valid and can be used in execution
"""


def test_load_config():
    pass


def test_check_config():
    import pytest
    from core.definitions import ConfigKeys, ConfigDefaultValues, ConfigMandatoryKeys
    from infra.config_utils import check_config

    # check empty config does not work
    bad_config1 = {}
    with pytest.raises(Exception):
        check_config(bad_config1)
        print(f"Expected {bad_config1} to be invalid, missing any keys")
    
    # check config without defaults does not work
    bad_config2 = {'a': 1, 'b': 2}
    with pytest.raises(Exception):
        check_config(bad_config2)
        print(f"Expected {bad_config2} to be invalid, missing mandatory keys")

    # check config with defaults but not correct values, does not work
    bad_config3 = {key: 1 for key in ConfigMandatoryKeys.get_all()}
    with pytest.raises(Exception):
        check_config(bad_config3)
        print(f"Expected {bad_config3} to be invalid")
    
    # check basic default config
    good_config = {key: 1 for key in ConfigMandatoryKeys.get_all()}
    good_config[ConfigKeys.Name] = "Good basic config"
    good_config[ConfigKeys.Description] = "A description"
    good_config[ConfigKeys.Workloads] = ['nst']
    good_config[ConfigKeys.Accelerators] = ConfigDefaultValues.Accelerators
    good_config[ConfigKeys.Timeout] = ConfigDefaultValues.Timeout
    assert check_config(good_config), f"Expected {good_config} to be valid"

    # check list of parallel workloads
    good_config[ConfigKeys.Name] = "Good parallel config"
    good_config[ConfigKeys.Workloads] = [['nst', 'sandstone']]
    assert check_config(good_config), f"Expected {good_config} to be valid"

    # check workload with extra data
    good_config[ConfigKeys.Name] = "Good config with data"
    good_config[ConfigKeys.Workloads] = [{ConfigKeys.Workload: 'nst', ConfigKeys.Timeout: 120}]
    assert check_config(good_config), f"Expected {good_config} to be valid"
    
    # check parallel workloads with extra data
    good_config[ConfigKeys.Name] = "Good parallel config with data"
    good_config[ConfigKeys.Workloads] = [['sandstone', {ConfigKeys.Workload: 'nst', ConfigKeys.Timeout: 120}]]
    assert check_config(good_config), f"Expected {good_config} to be valid"

    # check list of sequential workloads
    good_config[ConfigKeys.Name] = "Good sequential config"
    good_config[ConfigKeys.Workloads] = ['nst', 'sandstone']
    assert check_config(good_config), f"Expected {good_config} to be valid"

    # check sequential workloads with extra data
    good_config[ConfigKeys.Name] = "Good sequential config with data"
    good_config[ConfigKeys.Workloads] = ['sandstone', {ConfigKeys.Workload: 'nst', ConfigKeys.Timeout: 120}]
    assert check_config(good_config), f"Expected {good_config} to be valid"

    # check extra key
    good_config[ConfigKeys.Name] = "Good config with extra key"
    good_config["random key"] = "random value"
    assert check_config(good_config), f"Expected {good_config} to be valid"


def test_merge_config():
    from infra.config_utils import merge_config
    base_cfg = {'a': 1, 'b': 2}
    new_cfg = {'b': 3, 'c': 4}
    merged = merge_config(base_cfg, new_cfg)
    assert merged == {'a': 1, 'b': 3, 'c': 4}, f"Expected {merged} to be {'a': 1, 'b': 3, 'c': 4}"
    merged = merge_config(base_cfg, new_cfg, view_overridden=True)
    assert merged == ({'a': 1, 'b': 3, 'c': 4}, ['b']), f"Expected {merged} to be ({{'a': 1, 'b': 3, 'c': 4}}, ['b'])"