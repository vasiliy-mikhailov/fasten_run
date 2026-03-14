"""Canonical FastenRun examples.

These examples are intentionally data-only. They show both common use cases
and parameter coverage for every field on RunSpec and its nested models.
"""

from container_exec.models import AcceleratorSpec, MountSpec, ResourceLimits, RunSpec


PYTHON_VALUE_RUNSPEC = RunSpec(
    image="python:3.12-slim",
    command=("python", "-c", "print(2 + 2)"),
    limits=ResourceLimits(timeout_sec=30, memory="512m", cpus=1.0),
)

RUST_COMPILE_AND_RUN_RUNSPEC = RunSpec(
    image="rust:1.76",
    command=("bash", "-lc", 'echo "$RUST_CODE" > main.rs && rustc main.rs -O -o app && ./app'),
    env={"RUST_CODE": 'fn main() { println!("{}", 2 + 2); }'},
    limits=ResourceLimits(timeout_sec=30, memory="512m", cpus=1.0),
)

PYTEST_RUNSPEC = RunSpec(
    image="python:3.12-slim",
    command=("python", "-m", "pytest", "-q"),
    working_dir="/workspace",
    mounts=(MountSpec(source=".", target="/workspace", read_only=False),),
    limits=ResourceLimits(timeout_sec=120, memory="1g", cpus=1.0),
)

COVERAGE_JSON_RUNSPEC = RunSpec(
    image="python:3.12-slim",
    command=("bash", "-lc", "coverage run -m pytest && coverage json -o coverage.json && cat coverage.json"),
    working_dir="/workspace",
    mounts=(MountSpec(source=".", target="/workspace", read_only=False),),
    limits=ResourceLimits(timeout_sec=180, memory="1g", cpus=1.0),
)

ARBITRARY_SHELL_RUNSPEC = RunSpec(
    image="alpine:3.20",
    command=("sh", "-lc", "echo hello"),
    limits=ResourceLimits(timeout_sec=10, memory="128m", cpus=0.5),
)

COMPILE_VERIFICATION_RUNSPEC = RunSpec(
    image="rust:1.76",
    command=("bash", "-lc", 'echo "$RUST_CODE" > main.rs && rustc main.rs -O'),
    env={"RUST_CODE": 'fn main() { println!("ok"); }'},
    limits=ResourceLimits(timeout_sec=30, memory="512m", cpus=1.0),
)

LINT_RUNSPEC = RunSpec(
    image="python:3.12-slim",
    command=("python", "-m", "ruff", "check", "."),
    working_dir="/workspace",
    mounts=(MountSpec(source=".", target="/workspace", read_only=False),),
    limits=ResourceLimits(timeout_sec=60, memory="512m", cpus=1.0),
)

FORMATTING_CHECK_RUNSPEC = RunSpec(
    image="python:3.12-slim",
    command=("python", "-m", "black", "--check", "."),
    working_dir="/workspace",
    mounts=(MountSpec(source=".", target="/workspace", read_only=False),),
    limits=ResourceLimits(timeout_sec=60, memory="512m", cpus=1.0),
)

REPEATED_BENCHMARK_RUNSPEC = RunSpec(
    image="python:3.12-slim",
    command=("python", "bench.py", "--variant", "candidate-a"),
    env={"RUN_KIND": "benchmark"},
    working_dir="/workspace",
    mounts=(MountSpec(source=".", target="/workspace", read_only=False),),
    limits=ResourceLimits(timeout_sec=30, memory="512m", cpus=1.0),
)

CODE_GRADING_RUNSPEC = RunSpec(
    image="python:3.12-slim",
    command=("python", "grader.py"),
    env={"SUBMISSION": "candidate source here"},
    working_dir="/workspace",
    mounts=(MountSpec(source=".", target="/workspace", read_only=False),),
    limits=ResourceLimits(timeout_sec=30, memory="512m", cpus=1.0),
)

REGRESSION_REPLAY_RUNSPEC = RunSpec(
    image="python:3.12-slim",
    command=("python", "replay.py", "--case", "stored-case-17"),
    env={"CANDIDATE": "candidate source here"},
    working_dir="/workspace",
    mounts=(MountSpec(source=".", target="/workspace", read_only=False),),
    limits=ResourceLimits(timeout_sec=30, memory="512m", cpus=1.0),
)

GENERATED_PATCH_VALIDATION_RUNSPEC = RunSpec(
    image="python:3.12-slim",
    command=("bash", "-lc", "git apply patch.diff && pytest -q && python -m ruff check ."),
    env={"PATCH_TEXT": "..."},
    working_dir="/workspace",
    mounts=(
        MountSpec(source=".", target="/workspace", read_only=False),
        MountSpec(source="./patches", target="/patches", read_only=True),
    ),
    limits=ResourceLimits(timeout_sec=120, memory="512m", cpus=1.0),
)

SANDBOXED_FAILURE_REPRODUCTION_RUNSPEC = RunSpec(
    image="python:3.12-slim",
    command=("python", "repro.py", "--seed", "1234"),
    env={"INPUT_PAYLOAD": "..."},
    working_dir="/workspace",
    mounts=(MountSpec(source=".", target="/workspace", read_only=False),),
    limits=ResourceLimits(timeout_sec=30, memory="512m", cpus=1.0),
    name="repro-seed-1234",
)

ALL_PARAMETERS_RUNSPEC = RunSpec(
    image="my-inference-image:latest",
    command=("python", "score.py", "--batch", "32"),
    env={"MODEL_PATH": "/models/model.bin", "TOKENIZERS_PARALLELISM": "false"},
    working_dir="/workspace",
    limits=ResourceLimits(timeout_sec=90, memory="4g", cpus=2.0, pids_limit=256),
    network_enabled=False,
    read_only_root_fs=True,
    mounts=(
        MountSpec(source="./workspace", target="/workspace", read_only=False),
        MountSpec(source="./models", target="/models", read_only=True),
    ),
    accelerators=(
        AcceleratorSpec(kind="gpu", count=1, exclusive=True),
        AcceleratorSpec(kind="npu", device_ids=("npu0",), vendor="intel"),
    ),
    user="1000:1000",
    name="llm-score-run",
)
