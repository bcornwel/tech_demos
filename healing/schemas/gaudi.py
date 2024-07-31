"""
This file contains the schematic for the gaudi_result.log file
"""


from definitions import RegexStrings, ResultDefinitions

schema = {
    "pattern": RegexStrings.AlphaNumeric,
    "type": "object",
    "propertyNames": {
        "pattern": RegexStrings.Hashed_Host,
        "error message": f"This data should be a hostname that matches the format {RegexStrings.Hashed_Host}"
    },
    "additionalProperties": {
        "type": "object",
        "properties": {
            "Host": {
                "type": "string",
                "pattern": RegexStrings.AlphaNumeric,
                "error message": f"This data should be a hostname that matches the format {RegexStrings.AlphaNumeric}"
            },
            "Device": {
                "type": "string",
                "pattern": r"\(accel[0-9]{1,2}\)",
                "error message": f"This data should contain a string that matches the format \(accel[0-9]{1,2}\)"
            },
            "PCI_deviceID": {
                "type": "string",
                "pattern": r"[0-9]{1,4}:[0-9]{1,2}:[0-9]{1,2}.[0-9]{1,5}",
                "error message": f"This data should contain a string that matches the format [0-9]{1,4}:[0-9]{1,2}:[0-9]{1,2}.[0-9]{1,5}"
            },
            "Ping": {
                "type": "string",
                "pattern": r"[0-9]/[0-9]",
                "error message": f"This data should contain a string that matches the format [0-9]/[0-9]"
            },
            "MTU": {
                "type": "string",
                "pattern": r"[0-9]{4}",
                "error message": f"This data should contain a string that matches the format [0-9]{4}"
            },
            "Driver": {
                "type": "string",
                "enum": ["habanalabs"],
                "error message": f"This data should contain 'habanalabs'"
            },
            "Synapse": {
                "type": "string",
                "pattern": r"[0-9].[0-9]{1,3}.[0-9]{1,2}-[a-z0-9]{1,7}",
                "error message": f"This data should contain a string that matches the format [0-9].[0-9]{1,3}.[0-9]{1,2}-[a-z0-9]{1,7}"
            },
            "L3_CFG": {
                "type": "string",
                "enum": ["YES", "NO"],
                "error message": f"This data should contain YES or NO"
            },
            "Clock_MHz": {
                "type": "string",
                "pattern": r"[0-9]{1,5}",
                "error message": f"This data should contain a string that matches the format [0-9]{1,5}"
            },
            "Status": {
                "type": "string",
                "enum": [ResultDefinitions.TestFilePass, ResultDefinitions.TestFileFail],
                "error message": f"This data should contain {ResultDefinitions.TestFilePass} or {ResultDefinitions.TestFileFail}"
            },
        }
    }
}


if __name__ == "__main__":
    from definitions import Strings
    print(Strings.NotStandalone)
