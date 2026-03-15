import json
from types import SimpleNamespace

from container_exec import cli
from container_exec.models import RawExecutionResult, RunSpec


class FakeExecutor:
    def __init__(self, result: RawExecutionResult):
        self.result = result
        self.calls = []

    def execute(self, spec: RunSpec) -> RawExecutionResult:
        self.calls.append(spec)
        return self.result


class FakeRuntime:
    def __init__(self, client):
        self.client = client


def test_cli_run_builds_runspec_and_prints_json(monkeypatch, capsys) -> None:
    fake_client = object()
    fake_executor = FakeExecutor(
        RawExecutionResult(timed_out=False, exit_code=0, stdout="4\n", stderr="")
    )

    monkeypatch.setattr(cli, "_docker_from_env", lambda: fake_client)
    monkeypatch.setattr(cli, "DockerRuntime", FakeRuntime)
    monkeypatch.setattr(cli, "ContainerExecutor", lambda runtime: fake_executor)

    exit_code = cli.main(
        [
            "run",
            "--image",
            "python:3.12-slim",
            "--timeout-sec",
            "45",
            "--cpus",
            "1.5",
            "--memory",
            "768m",
            "--pids-limit",
            "32",
            "--env",
            "A=B",
            "--read-only-root-fs",
            "--name",
            "demo-run",
            "--",
            "python",
            "-c",
            "print(2 + 2)",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    sent = fake_executor.calls[0]

    assert exit_code == 0
    assert sent.image == "python:3.12-slim"
    assert sent.command == ("python", "-c", "print(2 + 2)")
    assert sent.env == {"A": "B"}
    assert sent.limits.timeout_sec == 45
    assert sent.limits.cpus == 1.5
    assert sent.limits.memory == "768m"
    assert sent.limits.pids_limit == 32
    assert sent.read_only_root_fs is True
    assert sent.name == "demo-run"
    assert payload == {
        "timed_out": False,
        "exit_code": 0,
        "stdout": "4\n",
        "stderr": "",
    }


def test_cli_returns_124_on_timeout(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_docker_from_env", lambda: object())
    monkeypatch.setattr(cli, "DockerRuntime", FakeRuntime)
    monkeypatch.setattr(
        cli,
        "ContainerExecutor",
        lambda runtime: FakeExecutor(
            RawExecutionResult(timed_out=True, exit_code=None, stdout="", stderr="")
        ),
    )

    exit_code = cli.main(["run", "--image", "alpine:3.20", "--", "sh", "-lc", "sleep 5"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 124
    assert payload["timed_out"] is True
