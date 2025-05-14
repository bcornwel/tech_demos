from core.definitions import Workloads, ConfigKeys, LogLevels


config = {
    ConfigKeys.Name: "Example",
    ConfigKeys.Description: "Example test",
    ConfigKeys.Nodes: None,  # nodes to run on
    ConfigKeys.Accelerators: 8,  # number of accelerators to run on
    ConfigKeys.Workloads: [Workloads.nst, Workloads.sandstone],  # list of workloads to run
    ConfigKeys.OptionalWorkloads: [Workloads.cornet],  # list of optional workloads to run
    ConfigKeys.Delay: 0,  # delay between tests in seconds
    ConfigKeys.Timeout: 120,  # max timeout in seconds
    ConfigKeys.Duration: 60,  # minimum duration of run in seconds
    ConfigKeys.MaximumMemory: 32,  # maximum memory to use in GB
    ConfigKeys.MaximumPower: 300,  # maximum power to use in watts
    ConfigKeys.MaximumTemperature: 50,  # maximum temperature to use in degrees celsius
    ConfigKeys.MaximumCores: 8,  # maximum number of cores to use
    ConfigKeys.MaximumThreads: 8,  # maximum number of threads to use
    ConfigKeys.MinimumMemory: 2,  # minimum memory to use in GB
    ConfigKeys.MinimumCores: 1,  # minimum number of cores to use
    ConfigKeys.MinimumThreads: 1,  # minimum number of threads to use
    ConfigKeys.Debug: False,  # debug mode
    ConfigKeys.LogLevel: LogLevels.Info, # log level
}
