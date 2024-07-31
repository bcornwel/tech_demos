"""
This file contains the schematic for the kernel_result.log file
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
            "KERNEL": {
                "type": "string",
                "pattern": r"[0-9]{1,2}.[0-9]{1,2}.[0-9]{1,2}",
                "error message": f"This data should contain a string that matches the format [0-9]{1,2}.[0-9]{1,2}.[0-9]{1,2}"
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
