from container_exec.executor import ContainerExecutor
from container_exec.models import RawExecutionResult, ResourceLimits, RunSpec


class FakeRuntime:
    def __init__(self, result: RawExecutionResult):
        self.result = result
        self.calls = []

    def run(self, task: RunSpec) -> RawExecutionResult:
        self.calls.append(task)
        return self.result


def test_executor_delegates_to_runtime() -> None:
    expected = RawExecutionResult(timed_out=False, exit_code=0, stdout="ok", stderr="")
    runtime = FakeRuntime(expected)
    executor = ContainerExecutor(runtime)
    task = RunSpec(
        image="python:3.12-slim",
        command=("python", "-c", "print(2 + 2)"),
        limits=ResourceLimits(timeout_sec=30, memory="512m", cpus=1.0),
    )

    actual = executor.execute(task)

    assert actual == expected
    assert runtime.calls == [task]
