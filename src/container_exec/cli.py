from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .docker_runtime import DockerRuntime
from .executor import ContainerExecutor
from .models import MountSpec, ResourceLimits, RunSpec


def _docker_from_env():
    import docker
    return docker.from_env()


def _parse_env(values: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"invalid --env value: {item!r}; expected KEY=VALUE")
        key, value = item.split("=", 1)
        env[key] = value
    return env


def _parse_mount(value: str) -> MountSpec:
    parts = value.split(":")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError(
            f"invalid --mount value: {value!r}; expected SOURCE:TARGET[:ro|rw]"
        )
    source = str(Path(parts[0]).expanduser().resolve())
    target = parts[1]
    mode = parts[2] if len(parts) == 3 else "ro"
    if mode not in ("ro", "rw"):
        raise argparse.ArgumentTypeError(
            f"invalid mount mode: {mode!r}; expected 'ro' or 'rw'"
        )
    return MountSpec(source=source, target=target, read_only=(mode == "ro"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fasten-run",
        description="Execute bounded container runs and return raw execution facts as JSON.",
    )
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    run = subparsers.add_parser("run", help="Run one container task")
    run.add_argument("--image", required=True, help="Container image to run")
    run.add_argument("--timeout-sec", type=int, default=30, help="Wall-clock timeout in seconds")
    run.add_argument("--cpus", type=float, default=1.0, help="CPU limit")
    run.add_argument("--memory", default="512m", help="Memory limit, e.g. 512m or 2g")
    run.add_argument("--pids-limit", type=int, default=None, help="PID limit")
    run.add_argument("--env", action="append", default=[], metavar="KEY=VALUE", help="Environment variable")
    run.add_argument(
        "--mount",
        action="append",
        default=[],
        metavar="SOURCE:TARGET[:ro|rw]",
        help="Bind mount specification",
    )
    run.add_argument("--workdir", default=None, help="Working directory inside the container")
    run.add_argument("--network-enabled", action="store_true", help="Enable networking")
    run.add_argument("--read-only-root-fs", action="store_true", help="Run with a read-only root filesystem")
    run.add_argument("--user", default=None, help="User inside the container, e.g. 1000:1000")
    run.add_argument("--name", default=None, help="Optional container name")
    run.add_argument("task_command", nargs=argparse.REMAINDER, help="Command to execute after --")
    return parser


def _build_runspec(args: argparse.Namespace) -> RunSpec:
    command = tuple(args.task_command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("fasten-run run requires a command after '--'")

    return RunSpec(
        image=args.image,
        command=command,
        env=_parse_env(args.env),
        working_dir=args.workdir,
        limits=ResourceLimits(
            timeout_sec=args.timeout_sec,
            cpus=args.cpus,
            memory=args.memory,
            pids_limit=args.pids_limit,
        ),
        network_enabled=args.network_enabled,
        read_only_root_fs=args.read_only_root_fs,
        mounts=tuple(_parse_mount(value) for value in args.mount),
        user=args.user,
        name=args.name,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command_name != "run":
        parser.error("unknown command")

    spec = _build_runspec(args)
    runtime = DockerRuntime(_docker_from_env())
    executor = ContainerExecutor(runtime)
    result = executor.execute(spec)

    print(
        json.dumps(
            {
                "timed_out": result.timed_out,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            ensure_ascii=False,
        )
    )

    if result.timed_out:
        return 124
    return int(result.exit_code or 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
