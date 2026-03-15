from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from container_exec.docker_runtime import DockerRuntime
from container_exec.executor import ContainerExecutor
from container_exec.models import ResourceLimits, RunSpec


def _check_prerequisites() -> tuple[object, list[str]]:
    problems: list[str] = []

    docker_cli = shutil.which("docker")
    if docker_cli is None:
        problems.append("docker CLI is not available on PATH")
    else:
        try:
            completed = subprocess.run(
                [docker_cli, "ps"],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip()
                problems.append(f"docker ps failed: {detail}")
        except Exception as exc:  # pragma: no cover - environment dependent
            problems.append(f"docker ps could not be executed: {exc}")

    try:
        import docker as docker_module
    except Exception as exc:  # pragma: no cover - environment dependent
        problems.append(f"python Docker SDK is not importable: {exc}")
        return None, problems

    try:
        client = docker_module.from_env()
        client.ping()
    except Exception as exc:  # pragma: no cover - environment dependent
        problems.append(f"docker daemon is not reachable from docker.from_env(): {exc}")
        return None, problems

    return client, problems


def _require_integration_prerequisites():
    client, problems = _check_prerequisites()
    if problems:
        formatted = "\n".join(f"- {problem}" for problem in problems)
        pytest.fail(
            "FastenRun integration prerequisites are not met:\n"
            f"{formatted}\n\n"
            "Start Docker Desktop or make sure your Docker daemon/socket is available, then retry."
        )
    return client


@pytest.mark.integration
def test_integration_prerequisites_are_met() -> None:
    _require_integration_prerequisites()


@pytest.mark.integration
def test_e2e_python_run_returns_stdout() -> None:
    client = _require_integration_prerequisites()
    runtime = DockerRuntime(client)
    executor = ContainerExecutor(runtime)

    result = executor.execute(
        RunSpec(
            image="python:3.12-slim",
            command=("python", "-c", "print(2 + 2)"),
            limits=ResourceLimits(timeout_sec=60, memory="512m", cpus=1.0),
        )
    )

    assert result.timed_out is False
    assert result.exit_code == 0
    assert result.stdout.strip() == "4"
    assert result.stderr == ""


@pytest.mark.integration
def test_e2e_rust_compile_and_run_returns_stdout() -> None:
    client = _require_integration_prerequisites()
    runtime = DockerRuntime(client)
    executor = ContainerExecutor(runtime)

    result = executor.execute(
        RunSpec(
            image="rust:1.76",
            command=(
                "bash",
                "-lc",
                'cat <<\'RS\' > main.rs\nfn main() { println!("{}", 2 + 2); }\nRS\nrustc main.rs -O -o app && ./app',
            ),
            limits=ResourceLimits(timeout_sec=180, memory="1g", cpus=1.0),
        )
    )

    assert result.timed_out is False
    assert result.exit_code == 0
    assert result.stdout.strip() == "4"


@pytest.mark.integration
def test_e2e_cli_pytest_and_coverage_json(tmp_path: Path) -> None:
    _require_integration_prerequisites()

    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\n\n\ndef test_add():\n    assert add(2, 2) == 4\n"
    )

    cmd = [
        sys.executable,
        "-m",
        "container_exec.cli",
        "run",
        "--image",
        "python:3.12-slim",
        "--timeout-sec",
        "180",
        "--memory",
        "1g",
        "--cpus",
        "1.0",
        "--mount",
        f"{tmp_path}:/workspace:rw",
        "--workdir",
        "/workspace",
        "--",
        "bash",
        "-lc",
        "python -m pip install --quiet pytest coverage && coverage run -m pytest -q && coverage json -o -",
    ]

    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout

    payload = json.loads(completed.stdout)
    assert payload["timed_out"] is False
    assert payload["exit_code"] == 0
    report = json.loads(payload["stdout"])
    assert "files" in report
    assert any(name.endswith("calc.py") for name in report["files"])
