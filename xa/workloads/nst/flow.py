from core.workload import WorkloadBase

class Workload(WorkloadBase):
    def __init__(self) -> None:
        config = "workloads/nst/config.py"
        super().__init__(config)

    def setup(self):
        self._setup()  # do not remove

    def run(self):
        self._run()  # do not remove
        self.log.info("Testing nst workload")
        self.log.info(f"NST config: {self.cfg}")
        import subprocess
        subprocess.check_output(f"{self.binary} --test_mode -t individual")

    def teardown(self):
        self._teardown()  # do not remove

    def verify(self):
        self._verify()  # do not remove
