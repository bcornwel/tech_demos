"""
This file can be used as a main entry point for running all pytest functionality
"""


if __name__ == "__main__":
    import pytest
    import os
    import sys
    from infra.file_utils import get_project_root
    from infra.log_utils import get_log
    from infra.proc_utils import set_exit_handler
    from _test.testing_utils import clear_logs
    extraneous_args = []
    start_idx = -1
    for i, arg in enumerate(sys.argv):
        if "_test" in arg or "__main__" in arg:
            start_idx = i+1
            break
    if start_idx >= 0 and len(sys.argv) > start_idx:
        extraneous_args = sys.argv[start_idx:]
    """
    NOTE: extraneous args is used to pass other pytest args that may not be standard
    For example, -x is used to exit on the first failure, in case you have a specific test in mind and want to see the failure
    """
    get_log().info(f"Running pytest with args: {extraneous_args}")
    set_exit_handler(profiling="--profiling" in sys.argv)
    clear_logs(["unit_test.log"])

    exit_code = pytest.main(["--rootdir", str(get_project_root()), "--cache-clear", "--log-file=unit_test.log", "--log-level=debug", *extraneous_args])
    if os.environ["TERM_PROGRAM"] != "vscode":  # don't throw this useless exception when debugging in vs code
        sys.exit(exit_code)
