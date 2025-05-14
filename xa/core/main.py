"""
This file contains the main function for the XA Scale application
"""

import os
from infra import arg_utils
from infra import config_utils
from infra import file_utils
from infra import log_utils
from infra import sys_utils
from core import scheduler
from core import workload


def main():
    args = arg_utils.parse_args()
    if args.seed:
        random = sys_utils.Random(seed=args.seed)
    log = log_utils.get_log(log_level=args.log, verbose=args.verbose)
    if args.schedule and args.config:  # create schedule
        config = config_utils.load_config(args.config)
        schedule = scheduler.make_schedule(config)
        schedule_path = os.path.join(file_utils.get_output_root(args.output), "schedule.json")
        scheduler.save_schedule(schedule, schedule_path)
        log.info(f"Schedule saved to: {schedule_path}")
    elif args.run:
        schedule = scheduler.load_schedule(args.run)
        log.info(f"Running schedule: {schedule}")
        data = scheduler.run_schedule(schedule)
        # verify that the schedule was run correctly by analyzing data and checking workload verification functionality
        workload.verify_workload_output(data)
    elif args.config:  # run config
        log.info(f"Using configuration: {args.config}")
        config = config_utils.load_config(args.config)
        schedule = scheduler.make_schedule(config)
        log.info(f"Running schedule: {schedule}")
        data = scheduler.run_schedule(schedule)
        # verify that the schedule was run correctly by analyzing data and checking workload verification functionality
        workload.verify_workload_output(data)
    elif args.list:
        log.info("Available configurations")
        config_utils.list_configs()
        log.info("Available workloads")
        workload.list_workloads()
    elif args.help:
        arg_utils.print_help()
    elif args.version:
        arg_utils.print_version()
    elif args.check:
        config_utils.check_config(args.check)
    else:
        log.error("No valid arguments provided, exiting")
        arg_utils.print_help()
    log.info("XA-Scale finished")


if __name__ == "__main__":
    main()