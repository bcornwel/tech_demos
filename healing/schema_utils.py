import json
import jsonschema
import os
from pathlib import Path

from definitions import Directories
from utils import safe_path, get_project_root, import_module_from_path


class Schemas(dict):
    """
    Consolidates schema data

    builds an object capable of access via field access or dict item access regardless of extension
    the following examples all load the same schema
    Schemas.example_schema
    Schemas.example_schema.json
    Schemas["example_schema"]
    Schemas["example_schema.json"]
    """
    def __init__(self):
        self.all_schemas = []
        schema_path = safe_path(Path(get_project_root(), Directories.Schemas), relative=False)
        schema_paths = [schema_path]
        for path in schema_paths:
            for file in path.iterdir():
                if file.name.endswith(".py") and not "__init__" in file.name:
                    schema = import_module_from_path(file, relative=False).schema
                elif file.name.endswith(".json"):
                    with open(file, 'r') as schema:
                        schema = json.loads(schema.read())
                else:
                    # print(f"Skipping non-functional file in schema dir: '{file}'")
                    continue
                jsonschema.Draft202012Validator.check_schema(schema)
                schema_file = os.path.basename(file.name)
                self[schema_file] = schema
                no_ext = os.path.splitext(schema_file)[0]
                self[no_ext] = schema
                self.__setattr__(no_ext, schema)
                self.all_schemas.append(no_ext)


Schemas = Schemas()


def validate_schema(instance: dict | bool, schema: dict) -> None:
    """
    Wraps the jsonschma's validate function with some better error handling, especially useful in the case of custom error messages

    Args:
        instance (dict or bool): a json-like object to validate, generally a dict
        schema (dict): the schema to use to validate the instance

    Raises:
        SchemaValidationError: error validating the schema
    """
    try:
        jsonschema.validate(instance, schema)
        return instance
    except Exception as validation_exception:
        err = f"{validation_exception}"
        instance_str = f"{instance}"
        if len(instance_str) > 32:  # need to shrink this down
            instance_str = f"{instance_str[:32]}..."
        if "error message" in err:
            err_start = err.find("error message")+15
            err = err[err_start:]
            err_end = err.find("\n", err_start)
            err = err[:err_end]
            pattern_str = ""
            if "'pattern'" in err:
                pattern_start = err.find("'pattern'")
                pattern = err[pattern_start+11:].strip()
                err = err[:pattern_start].strip()
                pattern_str = f"\nUse regex pattern: {pattern}"
            raise jsonschema.ValidationError(f"Error validating {instance_str} because {err}{pattern_str}")
        else:
            raise jsonschema.ValidationError(f"Error validating {instance_str}\n{err}")


if __name__ == "__main__":
    from definitions import Strings
    print(Strings.NotStandalone)
