"""
This file contains the schematic for the gaudi_result.log file
"""


from core.definitions import ConfigKeys, ConfigMandatoryKeys, RegexStrings, Workloads

all_workloads = Workloads.get_all()

schema = {
    "type": "object",
    "properties": {
        ConfigKeys.Name: {
            "type": "string",
            "pattern": RegexStrings.AlphaNumericWithSpace,
            "error message": f"The config name should match the format {RegexStrings.AlphaNumericWithSpace}"
        },
        ConfigKeys.Workloads: {
            "type": "array",
            "items": {
                "anyOf": [
                    {
                        "type": "string",
                        "enum": [workload for workload in all_workloads]
                    },
                    {
                        "type": "array",
                        "items": {
                            "anyOf": [
                                {
                                    "type": "string",
                                    "enum": [workload for workload in all_workloads]
                                },
                                {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": [workload for workload in all_workloads]
                                    }
                                },
                                {
                                    "type": "object",
                                    "properties": {
                                        ConfigKeys.Workload: {
                                            "type": "string",
                                            "enum": [workload for workload in all_workloads]
                                        },
                                        "max_duration": {
                                            "type": "integer"
                                        },
                                        "accelerators": {
                                            "type": "integer"
                                        },
                                        "max_cores": {
                                            "type": "integer"
                                        },
                                        "max_threads": {
                                            "type": "integer"
                                        },
                                        "max_memory": {
                                            "type": "integer"
                                        },
                                        "description": {
                                            "type": "string"
                                        },
                                        "args": {
                                            "type": "string"
                                        },
                                        "system": {
                                            "type": "string"
                                        },
                                        "debug": {
                                            "type": "boolean"
                                        },
                                        "log_level": {
                                            "type": "string",
                                            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                                        }
                                    },
                                    "required": ["workload"],
                                }
                            ],
                        }
                    },
                    {
                        "type": "object",
                        "properties": {
                            ConfigKeys.Workload: {
                                "type": "string",
                                "enum": [workload for workload in all_workloads]
                            },
                            "max_duration": {
                                "type": "integer"
                            },
                            "accelerators": {
                                "type": "integer"
                            },
                            "max_cores": {
                                "type": "integer"
                            },
                            "max_threads": {
                                "type": "integer"
                            },
                            "max_memory": {
                                "type": "integer"
                            },
                            "description": {
                                "type": "string"
                            },
                            "args": {
                                "type": "string"
                            },
                            "system": {
                                "type": "string"
                            },
                            "debug": {
                                "type": "boolean"
                            },
                            "log_level": {
                                "type": "string",
                                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                            }
                        },
                        "required": [ConfigKeys.Workload],
                    }
                ]
            },
            "error message": f"The workloads value should be"
        },
        ConfigKeys.Timeout: {
            "type": "integer",
            "error message": f"The timeout value should be an integer"
        },
        ConfigKeys.Accelerators: {
            "type": "integer",
            "error message": f"The accelerator value should be an integer"
        },
        ConfigKeys.Description: {
            "type": "string",
            "pattern": RegexStrings.AlphaNumericWithSpace,
            "error message": "The description value should be a string"
        },
    },
    "required": ConfigMandatoryKeys.get_all()
}

# ConfigKeys.OptionalWorkloads: {} # should be the same as ConfigKeys.Workloads, when that's completely defined



if __name__ == "__main__":
    from self_healing.definitions import Strings
    print(Strings.NotStandalone)
