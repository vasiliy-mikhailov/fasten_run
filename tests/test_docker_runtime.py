
from container_exec.docker_runtime import DockerRuntime
from container_exec.models import MountSpec, RawExecutionResult, ResourceLimits, RunSpec


class FakeContainer:
    def __init__(self, *, container_id: str = "abc123", exit_code: int = 0, stdout: str = "", stderr: str = ""):
        self.id = container_id
        self._exit_code = exit_code
        self._stdout = stdout
        self._stderr = stderr
        self.wait_calls = []
        self.killed = False
        self.removed = False

    def wait(self, timeout: int):
        self.wait_calls.append(timeout)
        return {"StatusCode": self._exit_code}

    def logs(self, *, stdout: bool, stderr: bool):
        if stdout and not stderr:
            return self._stdout.encode("utf-8")
        if stderr and not stdout:
            return self._stderr.encode("utf-8")
        raise AssertionError("unexpected logs call")

    def kill(self):
        self.killed = True

    def remove(self, force: bool = False):
        self.removed = True


class TimeoutContainer(FakeContainer):
    def wait(self, timeout: int):
        self.wait_calls.append(timeout)
        raise TimeoutError("container timed out")


class FakeContainersApi:
    def __init__(self, container):
        self.container = container
        self.run_kwargs = None

    def run(self, **kwargs):
        self.run_kwargs = kwargs
        return self.container


class FakeLowLevelApi:
    def __init__(self, exit_code: int):
        self.exit_code = exit_code
        self.inspect_calls = []

    def inspect_container(self, container_id: str):
        self.inspect_calls.append(container_id)
        return {"State": {"ExitCode": self.exit_code}}


class FakeDockerClient:
    def __init__(self, container, exit_code: int = 0):
        self.containers = FakeContainersApi(container)
        self.api = FakeLowLevelApi(exit_code)


def test_docker_runtime_returns_raw_output_on_success() -> None:
    container = FakeContainer(exit_code=0, stdout="4\n", stderr="")
    client = FakeDockerClient(container, exit_code=0)
    runtime = DockerRuntime(client)
    task = RunSpec(
        image="python:3.12-slim",
        command=("python", "-c", "print(2 + 2)"),
        env={"A": "B"},
        limits=ResourceLimits(timeout_sec=30, memory="512m", cpus=1.0),
    )

    actual = runtime.run(task)

    assert actual == RawExecutionResult(
        timed_out=False,
        exit_code=0,
        stdout="4\n",
        stderr="",
    )
    assert container.wait_calls == [30]
    assert container.removed is True


def test_docker_runtime_forwards_supported_runspec_fields() -> None:
    container = FakeContainer(exit_code=0, stdout="ok", stderr="")
    client = FakeDockerClient(container, exit_code=0)
    runtime = DockerRuntime(client)
    task = RunSpec(
        image="rust:1.76",
        command=("bash", "-lc", "echo hi"),
        env={"RUST_CODE": "fn main() {}"},
        working_dir="/workspace",
        limits=ResourceLimits(timeout_sec=15, memory="512m", cpus=1.0, pids_limit=128),
        network_enabled=False,
        read_only_root_fs=True,
        mounts=(MountSpec(source=".", target="/workspace", read_only=False),),
        user="1000:1000",
        name="example-run",
    )

    runtime.run(task)

    assert client.containers.run_kwargs["image"] == "rust:1.76"
    assert client.containers.run_kwargs["command"] == ["bash", "-lc", "echo hi"]
    assert client.containers.run_kwargs["environment"] == {"RUST_CODE": "fn main() {}"}
    assert client.containers.run_kwargs["working_dir"] == "/workspace"
    assert client.containers.run_kwargs["mem_limit"] == "512m"
    assert client.containers.run_kwargs["nano_cpus"] == 1_000_000_000
    assert client.containers.run_kwargs["pids_limit"] == 128
    assert client.containers.run_kwargs["network_disabled"] is True
    assert client.containers.run_kwargs["read_only"] is True
    assert client.containers.run_kwargs["volumes"] == {".": {"bind": "/workspace", "mode": "rw"}}
    assert client.containers.run_kwargs["user"] == "1000:1000"
    assert client.containers.run_kwargs["name"] == "example-run"


def test_docker_runtime_omits_optional_docker_kwargs_when_not_requested() -> None:
    container = FakeContainer(exit_code=0, stdout="", stderr="")
    client = FakeDockerClient(container, exit_code=0)
    runtime = DockerRuntime(client)
    task = RunSpec(
        image="python:3.12-slim",
        command=("python", "-V"),
        limits=ResourceLimits(timeout_sec=3, memory=None, cpus=None, pids_limit=None),
        network_enabled=True,
        read_only_root_fs=False,
        mounts=(),
        user=None,
        name=None,
    )

    runtime.run(task)

    kwargs = client.containers.run_kwargs
    assert kwargs["image"] == "python:3.12-slim"
    assert kwargs["command"] == ["python", "-V"]
    assert kwargs["network_disabled"] is False
    assert "working_dir" not in kwargs
    assert "mem_limit" not in kwargs
    assert "nano_cpus" not in kwargs
    assert "pids_limit" not in kwargs
    assert "read_only" not in kwargs
    assert "volumes" not in kwargs
    assert "user" not in kwargs
    assert "name" not in kwargs


def test_docker_runtime_preserves_stdout_and_stderr_without_interpretation() -> None:
    container = FakeContainer(exit_code=17, stdout="tool stdout\nsecond line\n", stderr="tool stderr\n")
    client = FakeDockerClient(container, exit_code=17)
    runtime = DockerRuntime(client)
    task = RunSpec(
        image="python:3.12-slim",
        command=("python", "-m", "pytest", "-q"),
        limits=ResourceLimits(timeout_sec=20),
    )

    actual = runtime.run(task)

    assert actual == RawExecutionResult(
        timed_out=False,
        exit_code=17,
        stdout="tool stdout\nsecond line\n",
        stderr="tool stderr\n",
    )


def test_docker_runtime_returns_timeout_result_and_cleans_up() -> None:
    container = TimeoutContainer()
    client = FakeDockerClient(container, exit_code=137)
    runtime = DockerRuntime(client)
    task = RunSpec(
        image="python:3.12-slim",
        command=("python", "-c", "while True: pass"),
        limits=ResourceLimits(timeout_sec=5),
    )

    actual = runtime.run(task)

    assert actual == RawExecutionResult(
        timed_out=True,
        exit_code=None,
        stdout="",
        stderr="",
    )
    assert container.killed is True
    assert container.removed is True


def test_docker_runtime_handles_empty_stdout_and_stderr() -> None:
    container = FakeContainer(exit_code=0, stdout="", stderr="")
    client = FakeDockerClient(container, exit_code=0)
    runtime = DockerRuntime(client)
    task = RunSpec(
        image="alpine:3.20",
        command=("sh", "-lc", "true"),
        limits=ResourceLimits(timeout_sec=10),
    )

    actual = runtime.run(task)

    assert actual == RawExecutionResult(
        timed_out=False,
        exit_code=0,
        stdout="",
        stderr="",
    )
