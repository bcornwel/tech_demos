import os
from pathlib import Path
import re
import shutil
from core.definitions import ConfigKeys, RegexStrings, Strings, Directories
from infra.file_utils import import_module_from_path
from infra.log_utils import get_log
from infra.proc_utils import run_command


class WorkloadBase:
    name = None
    binary = None
    folder = None
    description = None

    def __init__(self, config) -> None:
        cfg = import_module_from_path(config).config
        self.name = cfg.get(ConfigKeys.Name, None)
        self.binary = cfg.get(ConfigKeys.Binary, None)
        self.description = cfg.get(ConfigKeys.Description, None)
        self.cfg = cfg
        self.log = get_log()

    def __str__(self) -> str:
        return str(self.name)

    def _setup(self, constraints=None):
        """
        Any setup that needs to be done before the workload is run
        """
        self.log.info(f"Setting up workload {self.name}")

    def setup(self, constraints=None):
        """
        Any setup that needs to be done before the workload is run
        """
        self._setup(constraints=constraints)

    def _run(self, constraints=None):
        """
        Run the workload
        """
        self.log.info(f"Running workload {self.name}")

    def run(self, constraints=None):
        """
        Run the workload
        """
        self._run(constraints=constraints)

    def _teardown(self, constraints=None):
        """
        Any cleanup that needs to be done after the workload is run
        """
        self.log.info(f"Tearing down workload {self.name}")

    def teardown(self, constraints=None):
        """
        Any cleanup that needs to be done after the workload is run
        """
        self._teardown(constraints=constraints)

    def _verify(self, constraints=None):
        """
        Verify that the workload output is correct
        """
        self.log.info(f"Verifying workload {self.name}")

    def verify(self, constraints=None):
        """
        Verify that the workload output is correct
        """
        self._verify(constraints=constraints)


def get_workload_module(name:str):
    if Directories.Workloads in name:
        # get the name of the workload, split on the separator used (/ or \ depending on the OS)
        name = name.split(name[name.index(Directories.Workloads)+len(Directories)])[1]
    workloads = list_workloads()
    if name not in workloads:
        raise ValueError(f"Workload {name} does not exist in {workloads}")
    return import_module_from_path(Path("workloads", name, "flow.py")).Workload()


def run_workload(name, config=None):
    """
    Run a workload by name
    use ResourceManager from infra.proc_utils
    """
    assert check_workload_integrity(name), f"Workload {name} is not valid"
    # get the workload class
    workload = get_workload_module(name)
    # run the workload
    workload.setup()
    workload.run()
    workload.teardown()
    workload.verify()


def list_workloads():
    """
    List all available workloads
    """
    import os
    workload_dir = os.listdir(Directories.Workloads)
    valid = []
    for folder in workload_dir:
        if os.path.isdir(Path(Directories.Workloads, folder)):
            valid.append(folder)
    return valid


def check_workload_integrity(workload_name: str, example=False):
    path = f"workloads/{workload_name}"
    assert os.path.isdir(path), f"Workload {workload_name} should exist in workloads/"
    
    # check config
    assert os.path.exists(f"{path}/config.py"), f"Workload {workload_name} should have a config.py script"
    conf_mod = import_module_from_path(f"{path}/config.py")
    assert hasattr(conf_mod, "config"), f"Workload {workload_name} should have a config dict in config.py"
    if example:
        if conf_mod.config.get(ConfigKeys.Binary, None) and os.path.exists(f"{path}/{conf_mod.config[ConfigKeys.Binary]}"):
            pass
        else:
            assert conf_mod.config.get(ConfigKeys.Download, None), f"{'Example workload' if example else 'Workload'} {workload_name} does not have a binary or download link in config.py"

    # check flow
    assert os.path.exists(f"{path}/flow.py"), f"Workload {workload_name} should have a flow.py script"
    flow_mod = import_module_from_path(f"{path}/flow.py")
    assert hasattr(flow_mod, "Workload"), f"Workload {workload_name} should have a Workload class in flow.py"
    workload = flow_mod.Workload()
    assert isinstance(workload, WorkloadBase), f"Workload {workload_name} should be an instance of WorkloadBase"
    assert hasattr(workload, "name"), f"Workload {workload_name} should have a name attribute"
    assert hasattr(workload, "binary"), f"Workload {workload_name} should have a binary attribute"
    assert hasattr(workload, "description"), f"Workload {workload_name} should have a description attribute"
    for attr in ["setup", "run", "teardown", "verify"]:
        assert hasattr(workload, attr), f"Workload {workload_name} should have a {attr} method"
        assert hasattr(workload, f"_{attr}"), f"Workload {workload_name} should have a _{attr} method"
    return True


def generate_workload(name:str, copy_from:str=None, example:str=None, test:bool=False):
    """
    Generate a workload folder and files based on the provided name and example
    """
    # create a folder in the workloads directory with a lowercase version of the workload name
    # if there is a path, copy the files from the path to the new folder
    # if there is an example, copy the example config/flow to the new folder, and change references
    # if there is no example or path, copy the files from workloads/example
    
    # check that the workload does not already exist
    assert name.lower() not in list_workloads(), f"Workload {name} already exists"

    # check whether the name is a url to download from, in which case need to download the workload, and also parse the name
    url = re.match(RegexStrings.Url, name)
    if url:
        # get the name of the workload from the url
        if "github" in url.group(0):
            name = url.group(0).split("/")[-1].split(".")[-1]
            # download the workload from github
            if not test:
                # make workloads/tmp directory just in case
                Path("workloads/tmp").mkdir(parents=True, exist_ok=True)
                out, err, code = run_command(f"git clone {url.group(0)} workloads/tmp/{name}")
                if "exists" in ''.join(out):
                    print(f"Workload {name} already exists")
            if copy_from:
                copy_from = [f"workloads/tmp/{name}", copy_from]
            else:
                copy_from = [f"workloads/tmp/{name}"]
        else:
            raise ValueError(f"Not sure how to process this url into a workload: {name}. Please download the contents and try rerunning with the the name of the workload and the new folder as the path")
    
    # create the folder
    Path(f"workloads/{name}").mkdir(parents=True, exist_ok=False)  # should not exist
    
    if copy_from:
        if not isinstance(copy_from, list):
            copy_from = [copy_from]
        for p in copy_from:
            if not os.path.exists(p):
                assert os.path.exists(f"workloads/{p}"), f"Path '{p}' should exist, or be a workload in workloads/"
                p = f"workloads/{p}"
            # copy the files from the path to the new folder
            shutil.copytree(p, f"workloads/{name}", dirs_exist_ok=True)
    if not example:
       example = "example"
    assert check_workload_integrity(example, example=True), f"Workload example to copy '{example}' should be valid"

    # copy config.py and flow.py from the example to the new folder
    # change references in the copied files
    with open(f"workloads/{example}/config.py", 'r') as f:
        config = f.read()
    config = re.sub(f"{example}", f"{name}", config, flags=re.IGNORECASE)
    with open(f"workloads/{name}/config.py", 'w') as f:
        f.write(config)
    with open(f"workloads/{example}/flow.py", 'r') as f:
        flow = f.read()
    flow = re.sub(f"{example}", f"{name}", flow, flags=re.IGNORECASE)
    with open(f"workloads/{name}/flow.py", 'w') as f:
        f.write(flow)
    assert check_workload_integrity(name), f"Workload '{name}' is not valid after being generated"
    return name

def verify_workload_output(data):
    """
    Verify that the workload output is correct for each workload in data
    """
    # call verify function(s) in workload(s)
    pass


if __name__ == "__main__":
    print(Strings.NotStandalone)
