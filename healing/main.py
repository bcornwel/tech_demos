import json
import os

from arg_utils import *
from definitions import *
from log_utils import *
from utils import *


def heal(args, log: Logger):
    log.info(f"Results directory provided: {args.results}")
    # parse cfg files
    error_map = load_json_file_2_dict(os.path.join(get_project_root(), FileNames.ErrorMap))
    action_map = load_json_file_2_dict(os.path.join(get_project_root(), FileNames.ActionMap))
    results_map = load_json_file_2_dict(os.path.join(get_project_root(), FileNames.ResultMap))
    actions = dict()  # contains actions and their run status
    # load the syscheck results
    syscheck_results = load_space_delimited_file(os.path.join(args.results, FileNames.SysCheckResults), headers=[KeyNames.Test, KeyNames.Result])
    # determine which tasks need to be executed - mapping from errors to action
    for test, data in syscheck_results.items():
        if ResultDefinitions.ResultFileFail == data[KeyNames.Result]:
            result_file_data = results_map.get(data[KeyNames.Test])
            assert result_file_data, f"Unable to get result file name for test {test}"
            test_results = load_space_delimited_file(os.path.join(args.results, result_file_data[KeyNames.File]), header_line=result_file_data[KeyNames.Header], use_hashes=True)
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


def rerun_syscheck(all=True):
    pass


def full_heal(args, log: Logger):
    host_data = heal(args=args, log=log)

    # TODO: execute interventions via ssh

    # TODO: better data saving mechanism
    output_file = os.path.join(args.output, FileNames.HealingResults)
    os.makedirs(args.output, mode=777, exist_ok=True)
    with open(output_file, 'w') as res_file:
        json.dump(host_data, res_file)
    if ArgNames.syscheck in args:
        # TODO: run syscheck again
        rerun_syscheck()
    return host_data

def report(host_data):
    # TODO: report results - API
    pass


if __name__ == "__main__":
    log = get_log()
    try:
        log.info("Self-Healing initiated")
        # parse input commands
        log.debug("Parsing args")
        args = parse_and_handle_args()
        if ArgNames.results in args and args.results is not None:
            output = full_heal(args=args, log=log)
            report(output)
        else:
            log.info("Results directory not provided")
        log.info("Self-Healing is done")
    except Exception as exc:
        err_msg = f"Encountered error: {exc}"
        import traceback
        try:
            log.info(err_msg)
            log.debug(traceback.format_exc())
        except:  # issue with logging is very bad
            print(err_msg)
            print(traceback.format_exc())
        exit(1)
    exit(0)