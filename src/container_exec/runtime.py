from typing import Protocol

from .models import RawExecutionResult, RunSpec


class ContainerRuntime(Protocol):
    def run(self, task: RunSpec) -> RawExecutionResult:
        ...
