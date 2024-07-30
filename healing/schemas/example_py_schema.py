"""
This file demonstrates what python schemas can look like, that can incorporate definitions from the project
"""


from definitions import RegexStrings

schema = {
    "type": "object",
    "properties": {
        "example name": {
            "type": "string",
            "pattern": RegexStrings.AlphaNumeric,
            "error message": f"This data should match the format {RegexStrings.AlphaNumeric}"
        },
        "example tuple": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "prefixItems": [
                {
                    "type": "string"
                },
                {
                    "type": "number"
                }
            ]
        },
        "example list": {
            "type": "array",
            "minItems": 1,
            "items": {
                "properties": {
                    "example dict of multiple formats": {
                        "anyOf": [
                            {
                                "properties": {
                                    "example list": {
                                        "type": "array",
                                        "minItems": 1,
                                        "maxItems": 10
                                    },
                                    "example number": {
                                        "type": "number"
                                    },
                                    "example value of any type": {
                                        "type": ["array", "string", "number", "boolean", "null"]
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "example enum": {
                                        "type": "string",
                                        "enum": [
                                            "option 1",
                                            "option 2",
                                            "option 3"
                                        ]
                                    },
                                    "example string": {
                                        "type": "string"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
    }
}

if __name__ == "__main__":
    from definitions import Strings
    print(Strings.NotStandalone)
