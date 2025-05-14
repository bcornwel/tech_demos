from core.workload import WorkloadBase

class Workload(WorkloadBase):
    def __init__(self) -> None:
        config = "workloads/example/config.py"
        super().__init__(config)

    def setup(self):
        self._setup()  # do not remove

    def run(self):
        self._run()  # do not remove
        self.log.info("Testing Example workload")

    def teardown(self):
        self._teardown()  # do not remove

    def verify(self):
        self._verify()  # do not remove
