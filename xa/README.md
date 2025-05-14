# XA-Scale (Xeon Accelerators at Scale) 
#### A multi-function framework for running cluster workloads

## Purpose
XA-Scale is a tool for testing Xeon accelerators with varied workload configurations.</br>
Customer workloads that run on accelerated servers include specialized code for running on accelerators, but also required code running on Xeon CPUs for coordination, file io, networking, etc.</br>
To validate that these accelerated systems are functional before the customers use them, we need to test them in a multitude of ways such that a customer would.</br>
This includes resource splitting, maximizing workloads, back-to-back tests, and a variety of content to target all components in a system.</br>
XA-Scale is intended to be able to run all those different configurations with a dynamic structure for running tests, and awareness of a cluster’s design to be able to target the different components simultaneously.

## Test plan
[Test Plan document](https://intel-my.sharepoint.com/:w:/r/personal/brit_thornwell_intel_com/Documents/XA-Scale.docx?d=wd9c588d0c12c45d882df5edf2fecb666&csf=1&web=1&e=dypRLK)


## Setup
Run `./setup.sh` to install the required packages and setup the environment.

## How to run
### Manually
For usage, run `./main.py -h` to see the available options.

Main parameters include:
* `-c` or `--config` to specify the configuration file to use
* `-l` or `--list` to list the available workloads

Most common usage will be to run with a configuration file, such as:
`./main.py -c config.py`

Optional parameters include:
* `-a`, `--all` to run all tests
* `-d`, `--duration` to set the minimum duration for the test
* `-e`, `--ex`, `--exclude` to exclude specific workloads
* `-i`, `--info` to show the system information
* `-L`, `--log` to set the log level
* `-o`, `--out`, `--output` to set the output directory
* `-p`, `--profile` to profile the tests
* `-S`, `--seed` to set a randomization seed for reproducibility
* `-t`, `--timeout` to set a timeout for the test
* `-v`, `--verbose` to enable verbose mode
* `-w`, `--wl`, `--workload` to run a specific test
* `--check` to check the configuration file
* `--test` to run in test mode
* `--version` to show the version info

### Container


## Supported Workloads
| Workload | Description | 