import json
import os
from subprocess import check_output

from arg_utils import *
from definitions import *
from log_utils import *
from utils import *


def determine_healing(results_dir: str | Path, log: Logger) -> dict:
    """
    Parses a results folder containing a results.log and several test result log files
    Determines based on which tests failed, what actions need to run
    Then maps those to interventions
    Finally, consolidates that down to unique actions per system

    Args:
        results_dir (str | Path): the results directory
        log (Logger): the logging object

    Returns:
        dict: the data which contains the hosts and how they map to the actions/interventions required
    """
    log.info(f"Results directory provided: {results_dir}")
    # parse cfg files
    error_map = load_json_file_2_dict(os.path.join(get_project_root(), FileNames.ErrorMap))
    action_map = load_json_file_2_dict(os.path.join(get_project_root(), FileNames.ActionMap))
    results_map = load_json_file_2_dict(os.path.join(get_project_root(), FileNames.ResultMap))
    actions = dict()  # contains actions and their run status
    # load the syscheck results
    syscheck_results = load_space_delimited_file(os.path.join(results_dir, FileNames.SysCheckResults), headers=[KeyNames.Test, KeyNames.Result])
    # determine which tasks need to be executed - mapping from errors to action
    for test, data in syscheck_results.items():
        if ResultDefinitions.ResultFileFail == data[KeyNames.Result]:
            result_file_data = results_map.get(data[KeyNames.Test])
            assert result_file_data, f"Unable to get result file name for test {test}"
            test_results = load_space_delimited_file(os.path.join(results_dir, result_file_data[KeyNames.File]), header_line=result_file_data[KeyNames.Header], use_hashes=True)
            for host_id, results in test_results.items():
                for res_name, res_val in results.items():
                    if ResultDefinitions.TestFileFail == res_val:
                        action = error_map.get(test, {}).get(res_name)
                        if not action:
                            log.warning(f"Unable to find solutions for {res_name} test failure in {test} suite")
                        else:
                            intervention = action_map.get(action[KeyNames.Action])
                            assert intervention is not None, f"Unable to find fix for {res_name} test failure in {test} suite even though there's supposed to be one"
                            actions.setdefault(host_id, {})
                            # act on action data if applicable
                            if KeyNames.Input in action:
                                if isinstance(action[KeyNames.Input], str):
                                    action[KeyNames.Input] = results[action[KeyNames.Input]]
                                elif isinstance(action[KeyNames.Input], list):
                                    action[KeyNames.Input] = [results[item] for item in action[KeyNames.Input]]
                                # TODO: implement other action input options such as code or looking at data from an external file
                            action_data = {action[KeyNames.Action]: intervention | action}
                            if action[KeyNames.Action] in actions[host_id]:
                                log.warning(f"Overriding action {action[KeyNames.Action]} for host id {host_id}")
                            actions[host_id].update(action_data)
    log.info(f"Analyzing {len(actions)} call{'s' if len(actions) > 1 else ''} for interventions")
    # bucket actions by host
    hosts = {}
    for host_id, data in actions.items():
        hostname = host_id[:-5]
        hosts.setdefault(hostname, {})
        for act_name, act_data in data.items():
            if act_name in hosts[hostname]:
                log.warning(f"Overriding action {act_name} for host {hostname}")
            hosts[hostname][act_name] = act_data
    log.info(f"{len(hosts)} host{'s' if len(hosts) > 1 else ''} need{'' if len(hosts) > 1 else 's'} interventions")
    return hosts


def execute_interventions(data: dict) -> dict:
    """
    Executes required interventions

    Args:
        data (dict): the host <--> intervention mapping

    Returns:
        dict: results of interventions
    """
    # TODO: do interventions, threaded/multiprocessed if multiple machines
    return data


def rerun_syscheck(all:bool=True):
    """
    Reruns syscheck and gets results, feeding them back into the determine_healing function

    Args:
        all (bool, optional): whether or not to rerun all tests. Defaults to True.
    """
    # check output results at devops.syscheck/<ClusterName>/results/syscheck_results_<Date>_<Time>
    # e.g. devops.syscheck/devtest/results/result_syscheck_2024-05-06_1405
    # TODO: determine how to get to devops.syscheck path and verify devtest or other cluster name
    # should be parallel to this directory probably
    output = check_output("./syscheck")


def heal(args: Namespace, log: Logger):
    """
    Does the majority of functionality for this tool including
    * determining what to run
    * running interventions
    * checking interventions worked
    * reporting results

    Args:
        args (Namespace): the arg structure containing which args were called and their parameters
        log (Logger): the logging object
    """
    log.debug("Determining what needs to be healed")
    host_data = determine_healing(args.results, log=log)

    log.debug("Saving intervention data")
    # TODO: better data saving mechanism
    output_file = os.path.join(args.output, FileNames.InterventionData)
    os.makedirs(args.output, mode=777, exist_ok=True)
    with open(output_file, 'w') as res_file:
        json.dump(host_data, res_file)

    log.debug("Executing interventions")
    results = execute_interventions(host_data)

    log.debug("Rerunning syscheck to determine if interventions solved the problem(s)")
    rerun_syscheck()
    log.debug("Determining if more problems need to be healed")
    new_host_data = determine_healing(args.results, log=log)
    if new_host_data:
        new_results = execute_interventions(new_host_data)

    log.debug("Saving intervention results")
    # TODO: better data saving mechanism
    output_file = os.path.join(args.output, FileNames.HealingResults)
    os.makedirs(args.output, mode=777, exist_ok=True)
    with open(output_file, 'w') as res_file:
        json.dump(new_results if new_results else results, res_file)
    
    log.debug("Reporting results")
    report(host_data)


def report(host_data: dict):
    """
    Reports the results of running interventions to the orchestration software

    Args:
        host_data (dict): the data which contains the hosts and how they map to the actions/interventions required
    """
    # TODO: report results - API
    pass


if __name__ == "__main__":
    exit_code = ExitCodes.Okay
    log = get_log()
    try:
        log.info("Self-Healing initiated")
        # parse input commands
        log.debug("Parsing args")
        args = parse_and_handle_args()
        if ArgNames.results in args and args.results is not None:  # results directory is provided
            heal(args=args, log=log)
        # TODO: handle other args that might appear
        else:
            log.info("Results directory not provided")
        log.info("Self-Healing is done")
    except Exception as exc:
        err_msg = f"Encountered error: {exc}"
        import traceback
        try:
            log.info(err_msg)
            log.debug(traceback.format_exc())
            exit_code = ExitCodes.Err
        except:  # issue with logging is very bad
            print(err_msg)
            print(traceback.format_exc())
            exit_code = ExitCodes.ErrNoLog
    dump_log_data_to_dir(log, args.output)
    exit(exit_code)