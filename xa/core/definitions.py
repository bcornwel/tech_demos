"""
This file contains common definitions, used to make development/debug easier by consolidating strings and constants
"""


class Definitions:
    _cached = []
    @classmethod
    def get_all(cls):
        if not cls._cached:
            cls._cached =[value for key, value in cls.__dict__.items() if not key.startswith("__") and not callable(value)]
        return cls._cached


class Commands(Definitions):
    """
    Commands to use in the program
    """
    Run = "run"  # run a workload
    List = "list"  # list available configurations and workloads
    Version = "version"  # return the version of the program
    Check = "check"  # check a workload exists in a good state
    Setup = "setup"  # setup a workload
    Teardown = "teardown"  # teardown a workload
    Verify = "verify"  # verify a workload


class ExitCodes(Definitions):
    """
    Program exit codes to use when returning from the command line
    """
    Okay = 0
    Err = 1
    ErrNoLog = 2


class FileNames(Definitions):
    """
    Names of key files to use
    """
    Commands = "commands.txt"
    ErrorLogName = "errors.log"
    LogName = "xa.log"
    Hosts = "hosts.txt"
    PreTestStats = "pre_test_stats.txt"
    PostTestStats = "post_test_stats.txt"
    StatDiff = "stat_diff.txt"


class Flags(Definitions):
    Debug = False


class LogLevels(Definitions):
    # reference logging._nameToLevel or https://docs.python.org/3/library/logging.html#levels
    Debug = "DEBUG"
    Info = "INFO"
    Warning = "WARNING"
    Error = "ERROR"
    Critical = "CRITICAL"


class ConfigKeys(Definitions):
    Accelerators = "accelerators"
    Args = "args"  # - info
    Binary = "binary" # - workload configs
    Debug = "debug"  # - info
    Delay = "delay"  # - constraint
    Description = "description"  # - info
    Download = "download"  # - workload config
    Duration = "duration"  # - constraint
    File = "file"  # temporary in configs
    LogLevel = "log_level"  # - info
    MaximumCores = "maximum_cores"  # - constraint
    MaximumMemory = "maximum_memory"  # - constraint
    MaximumPower = "maximum_power"  # - constraint
    MaximumTemperature = "maximum_temperature"  # - constraint
    MaximumThreads = "maximum_threads"  # - constraint
    MaximumWorkloads = "maximum_workloads"  # - constraint
    MinimumCores = "minimum_cores"  # - constraint
    MinimumMemory = "minimum_memory"  # - constraint
    MinimumThreads = "minimum_threads"  # - constraint
    MinimumWorkloads = "minimum_workloads"  # - constraint
    Name = "name"  # - info
    Nodes = "nodes"  # - info
    OptionalWorkloads = "optional_workloads"
    Run = "run"  # - workload config
    Seed = "seed"  # - info
    Timeout = "timeout"  # - constraint
    Workload = "workload"
    Workloads = "workloads"


class ConfigMandatoryKeys(Definitions):
    """
    Mandatory keys for the configuration file
    """
    Name = ConfigKeys.Name
    Description = ConfigKeys.Description
    Accelerators = ConfigKeys.Accelerators
    Workloads = ConfigKeys.Workloads
    Timeout = ConfigKeys.Timeout


class Workloads(Definitions):
    cornet = "cornet"
    floresta = "floresta"
    hl_qual = "hl_qual"
    llama2_70b = "llama2_70b"
    llama3_70b = "llama3_70b"
    llama_3_1_405b = "llama_3_1_405b"
    nst = "nst"
    sandstone = "sandstone"


class Accelerators(Definitions):
    Gaudi = "Gaudi"
    Gaudi2 = "Gaudi2"
    Gaudi3 = "Gaudi3"
    FalconShores = "FalconShores"
    JaguarShores = "JaguarShores"


class AcceleratorKeys(Definitions):
    Devices = "devices"
    Memory = "memory"
    NetworkBandwidth = "network_bandwidth"


class AcceleratorDefaults(dict):
    def __init__(self):
        super().__init__()
        self[Accelerators.Gaudi] = {
            AcceleratorKeys.Devices: 8,
        }
        self[Accelerators.Gaudi2] = {
            AcceleratorKeys.Devices: 8,
        }
        self[Accelerators.Gaudi3] = {
            AcceleratorKeys.Devices: 8,
        }
        self[Accelerators.FalconShores] = {
            AcceleratorKeys.Devices: 8,
        }
        self[Accelerators.JaguarShores] = {
            AcceleratorKeys.Devices: 8,
        }
AcceleratorDefaults = AcceleratorDefaults()


class Directories(Definitions):
    Results = "results"
    Configs = "configs"
    Workloads = "workloads"
    HostSharedDir = "/var/xa_scale_shared"
    ContainerSharedDir = "/xa_scale_shared"
    Test = "_test"  # where test files are stored    


class ConfigDefaultValues(Definitions):
    """
    Default values for the configuration file
    """
    Accelerator = Accelerators.Gaudi2
    Accelerators = AcceleratorDefaults[Accelerator][AcceleratorKeys.Devices]  # number of accelerators to run on - constraint
    Delay = 0  # delay between tests in seconds - constraint
    Debug = False  # - info
    Duration = 5*60  # minimum duration of run in seconds -> 5 minutes - constraint
    LogLevel = LogLevels.Info  # - info
    Nodes = None  # use the current system - info
    MaximumMemory = None  # use system maximum - constraint
    MaximumPower = None  # maximum power to use in watts - constraint
    MaximumTemperature = None  # maximum temperature to use in degrees celsius - constraint
    MaximumCores = None  # use system maximum - constraint
    MaximumThreads = None  # use system maximum - constraint
    MaximumWorkloads = 100  # maximum number of workloads to run - constraint
    MinimumMemory = 2  # minimum memory to use in GB - constraint
    MinimumCores = 1  # minimum number of cores to use - constraint
    MinimumThreads = 1  # minimum number of threads to use - constraint
    MinimumWorkloads = 1  # minimum number of workloads to run - constraint
    Seed = 12345  # seed for random number generation - info
    Timeout = 1*60*60  # max tool timeout in seconds -> 1 hour - constraint


class RegexStrings(Definitions):
    """
    Contains useful regex strings
    all regex string unless one-off tests should be located here
    """
    Alpha = r"[a-zA-Z]+"
    AlphaNumeric = r"[a-zA-Z\.0-9]+"
    AlphaNumericWithSpace = r"[a-zA-Z\.0-9 ]+"
    AnsiEscapes = r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
    BlockDelete = r"(?i)Delete from"
    BlockDrop = r"(?i)Drop (index|constraint|table|column|primary|foreign|check|database|view)"
    BlockSqlComment = r"--"
    Directory = r"([a-zA-Z]:\\\\)|(\/|\\|\\\\){0,1}(\w+(\/|\\|\\\\))*\w+(\/|\\|\\\\)*"
    FriendlyNameChars = r"[a-zA-Z0-9_\-\(\)\. ]+"  # friendly name characters
    Hashed_Host = r"[a-zA-Z\.0-9]+_[0-9]{4}"
    InputCommand = r"(<input(\.\w+\((?:\"[^\"]*\"|'[^']*'|[^()])*\))*>)"
    MarkdownLink = r"\[.*\]\(.*\)"
    Numeric = r"(0-9)+\.*(0-9)+"
    PathLike = r"((?:[^;]*/)*)(.*)"
    PathTraversal = r"(/|\\|\\\\)\.\.(/|\\|\\\\)"
    PcieDeviceId = r"[0-9]{1,4}:[a-z0-9]{1,2}:[0-9]{1,2}.[0-9]{1,5}"
    PythonFile = r"([a-zA-Z]:){0,1}(/|\\|\\\\){0,1}(\w+(/|\\|\\\\))*\w+\.py"
    StandardSpaceDelimiter = r"[ ]{1,}"
    LargeSpaceDelimiter = r"[ ]{2,}"
    Tuple = r"[a-zA-Z0-9_\(\)\,]"
    UnfriendlyChars = r"[^a-zA-Z0-9_\-\(\)\./: ]+"  # non-friendly name characters
    Url = r"http(s){0,1}:\/\/(((([0-1]*[0-9]*[0-9]\.|2[0-5][0-5]\.){3})([0-1]*[0-9]*[0-9]|2[0-5][0-5])(:[0-9]{0,4}|[0-5][0-9]{4}|6[0-5][0-5][0-3][0-5])*)|((\d*[a-zA-Z][a-zA-Z0-9\.]*(\-*))+\.[a-zA-Z0-9]{1,3}))((/[\w\-\.]*)*(\?\w+=\w+)*)*"
    Variable = r"[\w_\. ]+"


class Strings(Definitions):
    """
    Common strings to use
    """
    NotStandalone = "This file is not meant to be run by itself, it should be imported"
    Contact = "pse_svce_content@intel.com"
    Version = "0.1"


class TestDefaults(Definitions):
    """
    Default values to use
    """
    NodeId = 0

if __name__ == "__main__":
    print(Strings.NotStandalone)
