from core.definitions import ConfigKeys

config = {
    ConfigKeys.Name: "Example",
    ConfigKeys.Binary: "example_bin.py",
    ConfigKeys.Description: "Example test",
    ConfigKeys.Run: "python3 example_bin.py",
    "parameters": {
        "example": {
            "description": "Example parameter",
            "type": "int",
            "default": 0
        }
    },
    ConfigKeys.Download: ""
}