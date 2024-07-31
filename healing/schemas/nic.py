"""
This file contains the schematic for the nic_result.log file
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
            "HOST": {
                "type": "string",
                "pattern": RegexStrings.AlphaNumeric,
                "error message": f"This data should be a hostname that matches the format {RegexStrings.AlphaNumeric}"
            },
            "NIC": {
                "type": "string",
                "pattern": RegexStrings.Variable,
                "error message": f"This data should contain a string matching the format {RegexStrings.Variable}"
            },
            "IFACE": {
                "type": "string",
                "pattern": RegexStrings.AlphaNumeric,
                "error message": f"This data should contain a string matching the format {RegexStrings.AlphaNumeric}"
            },
            "STATE": {
                "type": "string",
                "enum": ["ACTIVE", "INACTIVE"],
                "error message": f"This data should contain ACTIVE or INACTIVE"
            },
            "RATE": {
                "type": "string",
                "pattern": r"[0-9]{1,4}",
                "error message": f"This data should contain a string matching the format [0-9]{1,4}"
            },
            "LAYER": {
                "type": "string",
                "enum": ["Ethernet"],
                "error message": f"This data should contain 'Ethernet'"
            },
            "MTU": {
                "type": "string",
                "pattern": r"[0-9]{1,5}",
                "error message": f"This data should contain a string matching the format [0-9]{1,5}"
            },
            "RESULT": {
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
