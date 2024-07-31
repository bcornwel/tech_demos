"""
This file contains the schematic for the fs_result.log file
"""

import os
from pathlib import Path

from definitions import Directories, FileNames, RegexStrings, ResultDefinitions
from utils import load_json_file_2_dict, get_project_root


test_names = list(load_json_file_2_dict(Path(get_project_root(), Directories.Configs, FileNames.ResultMap)).keys())  # get the names from the result map file


schema = {
    "type": "object",
    "propertyNames": {
        "enum": test_names
    },
    "additionalProperties": {
        "type": "object",
        "properties": {
            "Test": {
                "type": "string",
                "enum": test_names,
                "error message": f"This data should be a test name in the list of {test_names}"
            },
            "Result": {
                "type": "string",
                "enum": [ResultDefinitions.ResultFilePass, ResultDefinitions.ResultFileFail],
                "error message": f"This data should contain {ResultDefinitions.ResultFilePass} or {ResultDefinitions.ResultFileFail}"
            }
        }
    }
}

if __name__ == "__main__":
    from definitions import Strings
    print(Strings.NotStandalone)
