"""
This file contains the scheduling logic
This file consumes the workload, accelerator, and infrastructure packages
"""


from infra.arg_utils import ArgHelperActions
from core.definitions import ConfigKeys, ConfigDefaultValues, LogLevels, Strings, Workloads
from core.workload import WorkloadBase, get_workload_module
from infra.config_utils import load_config
from infra.file_utils import jsonify, load_data, save_json, import_module_from_path
from infra.log_utils import get_log
from infra.net_utils import verify_connection
from infra.proc_utils import ResourceManager
from infra.sys_utils import get_system_id, Random


class Info:
    """
    This class represents the information about the system and the constraints that the schedule should respect
    The information is used to define the test information, system and test constraints, and workload requirements
    """

    def __init__(self, 
                 name: str, 
                 description: str, 
                 nodes: str, 
                 debug: bool = False, 
                 log_level: str = LogLevels.Info,
                 seed: int = ConfigDefaultValues.Seed,
                 args: str = "",
                 max_duration: int = ConfigDefaultValues.Duration,
                 accelerators: int = ConfigDefaultValues.Accelerators,
                 max_cores: int = ConfigDefaultValues.MaximumCores,
                 max_threads: int = ConfigDefaultValues.MaximumThreads,
                 max_memory: int = ConfigDefaultValues.MaximumMemory,
                 min_memory: int = ConfigDefaultValues.MinimumMemory,
                 min_cores: int = ConfigDefaultValues.MinimumCores,
                 min_threads: int = ConfigDefaultValues.MinimumThreads,
                 min_workloads: int = ConfigDefaultValues.MinimumWorkloads,
                 max_workloads: int = ConfigDefaultValues.MaximumWorkloads,
                 timeout: int = ConfigDefaultValues.Timeout
                 ):
        self.name = name
        self.description = description
        self.args = args
        self.nodes = nodes
        self.debug = debug
        self.log_level = log_level
        assert self.log_level in LogLevels.get_all(), f"Invalid log level: {self.log_level}"
        self.seed = ArgHelperActions.valid_seed(seed)
        self.max_duration = max_duration
        assert ArgHelperActions.valid_duration(self.max_duration), f"Invalid duration: {self.max_duration}"
        self.accelerators = accelerators
        assert self.accelerators > 0, f"Invalid accelerators: {self.accelerators}"
        # TODO: assert accelerators isn't greater than system accelerators * number of systems
        self.max_cores = max_cores
        # TODO: assert max cores aren't greater than system cores
        self.max_threads = max_threads
        # TODO: assert max threads aren't greater than system threads
        self.max_memory = max_memory
        # TODO: assert max memory isn't greater than system memory * number of systems
        self.min_memory = min_memory
        assert self.min_memory > 0, f"Invalid minimum memory: {self.min_memory}"
        self.min_cores = min_cores
        assert self.min_cores > 0, f"Invalid minimum cores: {self.min_cores}"
        self.min_threads = min_threads
        assert self.min_threads > 0, f"Invalid minimum threads: {self.min_threads}"
        self.timeout = timeout
        self.min_workloads = min_workloads
        assert self.min_workloads > 0, f"Invalid minimum workloads: {self.min_workloads}"
        self.max_workloads = max_workloads
        assert self.max_workloads > 0, f"Invalid maximum workloads: {self.max_workloads}"
        assert ArgHelperActions.valid_duration(self.timeout), f"Invalid timeout: {self.timeout}"
    
    def to_json(self):
        return jsonify(self.__dict__)


class Load:
    """
    This class represents a load to be run on the system
    A load is a workload with constraints
    """

    def __init__(self, workload: str, info: Info):
        self.workload:str = workload
        self.info:Info = info
        self.mod:WorkloadBase = None  # don't import until runtime
    
    def to_json(self):
        return jsonify(self.__dict__)


class Step:
    """
    This class represents a step in the schedule
    A step is a combination of workloads to run and constraints to use
    """

    def __init__(self, workloads: list[Load], info: Info):
        self.workloads = workloads
        self.info = info
    
    def to_json(self):
        return jsonify(self.__dict__)


class Schedule:
    """
    This class represents a schedule of workloads, considering system constraints and timing
    The schedule should provide the workloads to use as well as the order in which to run them
    It should also provide the seeds used for randomization

    e.g. nst+sandstone+hl_qual for a minute
    sandstone for 1 minute  # optionally less, but should likely use the whole duration
    nst for 30 seconds followed by hl_qual for 30 seconds,  # optionally 20s and 40s, 50s and 10s, etc.
    """

    def __init__(self, steps: list, info: Info):
        self.steps:list[Step] = steps  # list of Step objects
        self.info:Info = info
    
    def to_json(self):
        return jsonify(self.__dict__)


class WorkloadOutput:
    stdout = ""
    stderr = ""
    returncode = 0
    folder = None
    log = None

    def __init__(self, stdout: str, stderr: str, returncode: int, folder: str, log: str):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.folder = folder
        self.log = log
    
    def to_json(self):
        return jsonify(self.__dict__)


def verify_schedule(schedule: Schedule) -> bool:
    """
    This function verifies that the schedule is valid
    """
    assert isinstance(schedule.steps, list), "Invalid schedule steps"
    assert len(schedule.steps) > 0, "Need at least one step in the schedule"
    for step in schedule.steps:
        assert isinstance(step, Step), "Invalid schedule step"
        assert isinstance(step.info, Info), "Invalid step info"
        for load in step.workloads:
            assert isinstance(load, Load), "Invalid step workload"
            assert isinstance(load.info, Info), "Invalid load info"
    assert isinstance(schedule.info, Info), "Invalid schedule info"
    return True


def load_schedule(file="schedule.json") -> Schedule:
    """
    This function loads a schedule from a file
    """
    schedule_data = load_data(file)
    schedule = Schedule(**schedule_data)
    assert verify_schedule(schedule), "Invalid schedule"
    return schedule 


def make_schedule(config: dict) -> Schedule:
    """
    This function creates a schedule based on the configuration
    """
    log = get_log()
    config = load_config(config, check=True)  # will either load it or convert it if necesssary, then check it
    info = Info(
                name=config.get(ConfigKeys.Name, None),
                description=config.get(ConfigKeys.Description, None),
                nodes=config.get(ConfigKeys.Nodes, [get_system_id()]),
                debug=config.get(ConfigKeys.Debug, ConfigDefaultValues.Debug),
                log_level=config.get(ConfigKeys.LogLevel, ConfigDefaultValues.LogLevel),
                seed=config.get(ConfigKeys.Seed, ConfigDefaultValues.Seed),
                args=config.get(ConfigKeys.Args, ''),
                max_duration=config.get(ConfigKeys.Duration, ConfigDefaultValues.Duration),
                accelerators=config.get(ConfigKeys.Accelerators, ConfigDefaultValues.Accelerators),
                max_cores=config.get(ConfigKeys.MaximumCores, ConfigDefaultValues.MaximumCores),
                max_threads=config.get(ConfigKeys.MaximumThreads, ConfigDefaultValues.MaximumThreads),
                max_memory=config.get(ConfigKeys.MaximumMemory, ConfigDefaultValues.MaximumMemory),
                max_workloads = config.get(ConfigKeys.MaximumWorkloads, ConfigDefaultValues.MaximumWorkloads),
                min_memory=config.get(ConfigKeys.MinimumMemory, ConfigDefaultValues.MinimumMemory),
                min_cores=config.get(ConfigKeys.MinimumCores, ConfigDefaultValues.MinimumCores),
                min_threads=config.get(ConfigKeys.MinimumThreads, ConfigDefaultValues.MinimumThreads),
                min_workloads = config.get(ConfigKeys.MinimumWorkloads, ConfigDefaultValues.MinimumWorkloads),
                timeout=config.get(ConfigKeys.Timeout, ConfigDefaultValues.Timeout)
            )
    assert info.name, "Invalid configuration: missing name"
    assert info.description, "Invalid configuration: missing description"
    
    # create the steps
    steps = []
    Random().seed(info.seed)
    optional_workloads = config.get(ConfigKeys.OptionalWorkloads, [])
    workload_data = config.get(ConfigKeys.Workloads, [])
    #TODO: insert optional workloads
    #TODO: check workload requirements/constraints are within system constraints
    for workload in workload_data:
        if isinstance(workload, list):
            # parallel workloads
            workloads = []
            for wl in workload:
                if isinstance(wl, dict):
                    # workload with additional data
                    workloads.append(Load(workload=wl.get(ConfigKeys.Workload, None), info=info))
                else:
                    workloads.append(Load(workload=wl, info=info))
            steps.append(Step(workloads=workloads, info=info))
        elif isinstance(workload, dict):
            # workload with additional data
            steps.append(Step(workloads=[Load(workload=workload.get(ConfigKeys.Workload, None), info=info)], info=info))
        else:
            # single workload
            steps.append(Step(workloads=[Load(workload=workload, info=info)], info=info))

    return Schedule(steps=steps, info=info)
    

def save_schedule(schedule: Schedule, file="schedule.json"):
    """
    This function saves the schedule to a file
    """
    save_json(schedule.to_json(), file)


def split_schedule(schedule: Schedule) -> dict:
    """
    Split schedule by system
    """
    # split the schedule into multiple schedules based on the system in the info object per step/load
    # return a dict of schedules based on the system id
    systems = {}
    for step in schedule.steps:
        for load in step.workloads:
            if load.info.system not in systems:
                systems[load.info.system] = []
            systems[load.info.system].append(load)


def run_schedule(schedule: Schedule) -> dict:
    """
    This function runs the schedule and returns a dictionary of output from the workloads
    """
    # ensure we can connect to any nodes
    for node in schedule.info.nodes:
        assert verify_connection(node), f"Cannot connect to node: {node}"
    # loop through the schedule steps
    # set seed before the step
    # run the workloads
    log = get_log()
    random = Random()  # gets the existing random object
    assert verify_schedule(schedule), "Invalid schedule"
    data = {}
    for step in schedule.steps:
        random.seed(step.info.seed)
        # setup
        for load in step.workloads:
            log.info(f"Setting up: {load.workload}")
            for node in load.info.nodes:
                log.info(f"on node: {node}")
                # run the workload on the node
                if node in [get_system_id(), '.']:
                    load.mod = get_workload_module(load.workload)
                    load.mod.setup()
                else:
                    # deploy the workload to the node
                    # TODO: deploy the workload to the node
                    pass
        # run
        for load in step.workloads:
            log.info(f"Running: {load.workload}")
            for node in load.info.nodes:
                log.info(f"Running on node: {node}")
                # run the workload on the node
                if node in [get_system_id(), '.']:
                    load.mod.run()
                else:
                    # deploy the workload to the node
                    # TODO: deploy the workload to the node
                    pass
        # teardown
        for load in step.workloads:
            log.info(f"Tearing down: {load.workload}")
            for node in load.info.nodes:
                log.info(f"Running on node: {node}")
                # run the workload on the node
                if node in [get_system_id(), '.']:
                    load.mod.teardown()
                else:
                    # deploy the workload to the node
                    # TODO: deploy the workload to the node
                    pass


if __name__ == "__main__":
    print(Strings.NotStandalone)
