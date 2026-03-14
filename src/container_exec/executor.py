from .models import RawExecutionResult, RunSpec
from .runtime import ContainerRuntime


class ContainerExecutor:
    def __init__(self, runtime: ContainerRuntime):
        self._runtime = runtime

    def execute(self, task: RunSpec) -> RawExecutionResult:
        return self._runtime.run(task)
