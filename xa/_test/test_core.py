"""
This file contains the tests for the core module
Functions are split by granular concept to make them easier to debug
"""

def test_schedule_generation():
    """
    Test the schedule generation function
    """
    # Test the schedule generation function
    import pytest
    from core.definitions import ConfigKeys, ConfigMandatoryKeys, Workloads
    from core.scheduler import make_schedule

    blank_config = {}
    with pytest.raises(Exception):  # should throw an exception if there's no data
        no_schedule = make_schedule(blank_config)
    
    partially_empty_config = {
                                ConfigKeys.Name: "Partially empty example"
                            }
    with pytest.raises(Exception):  # should throw an exception if there's no data
        no_schedule = make_schedule(partially_empty_config)

    # use everything in ConfigMandatoryKeys
    basic_config = {
                    ConfigKeys.Name: "Basic example",
                    ConfigKeys.Description: "Example basic test",
                    ConfigKeys.Accelerators: 8,  # number of accelerators to run on
                    ConfigKeys.Workloads: [Workloads.nst],  # list of workloads to run
                    ConfigKeys.Timeout: 120,  # max timeout in seconds
                }
    basic_schedule1 = make_schedule(basic_config)
    assert len(basic_schedule1.steps) == 1, "Basic schedule #1 should have 1 step"
    
    # write basic_config to python file in dict format
    with open("test_config.py", 'w') as f:
        f.write("config = " + str(basic_config))
    basic_schedule2 = make_schedule("test_config.py")
    assert len(basic_schedule2.steps) == 1, "Basic schedule #2 should have 1 step"

    sequential_config = {
                            ConfigKeys.Name: "Sequential example",
                            ConfigKeys.Description: "Example sequential test",
                            ConfigKeys.Accelerators: 8,  # number of accelerators to run on
                            ConfigKeys.Workloads: [Workloads.nst, Workloads.sandstone],  # list of workloads to run
                            ConfigKeys.Timeout: 120,  # max timeout in seconds
                        }
    sequential_schedule = make_schedule(sequential_config)
    assert len(sequential_schedule.steps) == 2, "Sequential schedule should have 2 steps"
    for step in sequential_schedule.steps:
        assert step.workloads[0].workload in [Workloads.nst, Workloads.sandstone], "Workload should be in the list of workloads"

    parallel_config = {
                        ConfigKeys.Name: "Parallel example",
                        ConfigKeys.Description: "Example parallel test",
                        ConfigKeys.Accelerators: 8,  # number of accelerators to run on
                        ConfigKeys.Workloads: [[Workloads.nst, Workloads.sandstone]],  # list of workloads to run
                        ConfigKeys.Timeout: 120,  # max timeout in seconds
                    }
    parallel_schedule = make_schedule(parallel_config)
    assert len(parallel_schedule.steps) == 1, "Parallel schedule should have 1 step"
    step = parallel_schedule.steps[0]
    assert len(step.workloads) == 2, "Parallel step should have 2 workloads"
    # make sure nst and sandstone are in the workloads
    assert any([load.workload == Workloads.nst for load in step.workloads]), "nst should be in the list of workloads"
    assert any([load.workload == Workloads.sandstone for load in step.workloads]), "sandstone should be in the list of workloads"

    complex_config = {
                        ConfigKeys.Name: "Complex example",
                        ConfigKeys.Description: "Example complex test",
                        ConfigKeys.Accelerators: 8,  # number of accelerators to run on
                        ConfigKeys.Workloads: [[{ConfigKeys.Workload: Workloads.nst, ConfigKeys.Args: "-t individual"}, Workloads.sandstone], [Workloads.cornet]],  # list of workloads to run
                        ConfigKeys.Timeout: 120,  # max timeout in seconds
                    }
    complex_schedule = make_schedule(complex_config)
    assert len(complex_schedule.steps) == 2, "Complex schedule should have 2 steps"
    step1 = complex_schedule.steps[0]
    assert len(step1.workloads) == 2, "Parallel step should have 2 workloads"
    # make sure nst and sandstone are in the workloads
    assert any([load.workload == Workloads.nst for load in step1.workloads]), "nst should be in the list of workloads"
    assert any([load.workload == Workloads.sandstone for load in step1.workloads]), "sandstone should be in the list of workloads"
    step2 = complex_schedule.steps[1]
    assert len(step2.workloads) == 1, "Single step should have 1 workload"
    # make sure cornet is in the workloads
    assert step2.workloads[0].workload == Workloads.cornet, "cornet should be in the list of workloads"

    broken_config = {
                        ConfigKeys.Name: "Broken example",
                        ConfigKeys.Description: "Example broken test",
                        ConfigKeys.Accelerators: -1,  # number of accelerators to run on
                        ConfigKeys.Workloads: [Workloads.nst, Workloads.sandstone],  # list of workloads to run
                        ConfigKeys.Timeout: -5,  # max timeout in seconds
                    }
    with pytest.raises(AssertionError):  # should throw an exception since accelerators and timeout are invalid values
        no_schedule = make_schedule(broken_config)

    impossible_config = {
                            ConfigKeys.Name: "Impossible example",
                            ConfigKeys.Description: "Example impossible test",
                            ConfigKeys.Accelerators: 8,  # number of accelerators to run on
                            ConfigKeys.Workloads: [Workloads.nst, Workloads.sandstone],  # list of workloads to run
                            ConfigKeys.Timeout: 0,  # max timeout in seconds
                        }
    with pytest.raises(AssertionError):
        no_schedule = make_schedule(impossible_config)


def test_schedule_run():
    """
    Test the schedule run function
    """
    import pytest
    from core.scheduler import run_schedule, Schedule
    empty_schedule = Schedule([], None)
    with pytest.raises(Exception):
        run_schedule(empty_schedule)
        print(f"Expected {empty_schedule} to be an invalid schedule, missing any data")

    # test single workload schedule, sequential workloads schedule, parallel workloads schedule, complex schedule, and broken schedule
    


def test_schedule_timing():
    """
    Test the schedule run with interesting timing 
    """
    # test the schedule with no delays, some delays, workloads that run for too long, and workloads that don't meet minimum time