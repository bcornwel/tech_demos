"""
This file should contain functions to test the workload generation pipeline, loading, configuration analysis, and limited schedule building
It should also verify that the current workloads are valid and can be used in execution
"""


def test_verify_workloads_exist():
    from core.definitions import Workloads
    from core.workload import check_workload_integrity, list_workloads
    wls = list_workloads()
    # assert len(wls) == len(Workloads.get_all()), "Known workloads (in core.definitions) should be the same length as actual workloads in workloads/"
    # for wl in wls:
    #     assert check_workload_integrity(wl), f"Workload {wl} should be valid"
    # TODO: uncomment the above lines after implementing the workloads


def test_workload_generation():
    from core.workload import generate_workload
    from pathlib import Path
    import os
    import pytest
    
    test_workloads = []

    def generate(name, path=None, example=None):
        test_workloads.append(name)
        new_name = generate_workload(name, path, example)
        test_workloads.append(new_name)

    try:
        # generate a workload without a reference or copying files
        generate("test1", path="", example="")

        # generate a workload with a reference to example and not copying files
        generate("test2", path="", example="example")

        # generate a workload with a reference to example and copying files from test2
        generate("test3", path="workloads/test2", example="example")

        # fail to generate a workload with a reference to test1 and copying files from test2, but test1 doesn't have the required
        with pytest.raises(Exception):
            generate("test4", path="workloads/test2", example="test1")

        # generate a workload from a url and no references or examples
        generate("https://github.com/HabanaAI/hccl_demo", path="", example="")

        # generate a workload from a url and a reference to example
        generate("https://github.com/intel-innersource/applications.validation.sandstone.sandstone", path="", example="example")

    # catch and raise exceptions with additional messages depending on the error
    except Exception as e:
        if isinstance(e, AssertionError) or isinstance(e, FileNotFoundError):
            raise Exception(f"{e} - Are you sure you used the correct path and example?")
        elif isinstance(e, FileExistsError):
            raise Exception(f"{e} - Are you sure the workload doesn't already exist?")
        raise Exception(f"{e}")

    finally:
        # clear test workload directories
        for wl in test_workloads:
            # remove directory at workloads/wl
            path = Path(f"workloads/{wl}")
            if path.exists():
                # remove the directory even if it's not empty
                os.system(f"rm -rf {path}")