# FastenRun Specification

## Goal

Provide a minimal execution boundary for running arbitrary tasks inside a container runtime.

The **main goal** is to execute **LLM-generated programs** under strict **CPU**, **memory**, and **time** limits without interpreting task semantics.

## Ubiquitous language

### RunSpec
Input object describing one container run:
- `image: str`
- `command: tuple[str, ...]`
- `env: dict[str, str]`
- `working_dir: str | None`
- `limits: ResourceLimits`
- `network_enabled: bool`
- `read_only_root_fs: bool`
- `mounts: tuple[MountSpec, ...]`
- `accelerators: tuple[AcceleratorSpec, ...]`
- `user: str | None`
- `name: str | None`

### ResourceLimits
- `timeout_sec: int`
- `cpus: float | None`
- `memory: str | None`
- `pids_limit: int | None`

### MountSpec
- `source: str`
- `target: str`
- `read_only: bool`

### AcceleratorSpec
- `kind: str`
- `count: int | None`
- `device_ids: tuple[str, ...]`
- `vendor: str | None`
- `memory: str | None`
- `exclusive: bool`

### RawExecutionResult
Output object describing raw runtime facts:
- `timed_out: bool`
- `exit_code: int | None`
- `stdout: str`
- `stderr: str`

## Behavioral rules

1. The executor delegates to a runtime abstraction.
2. The runtime must pass image, command, env, supported limits, and supported isolation settings to the concrete container system unchanged.
3. If the runtime wait step exceeds `limits.timeout_sec`, the runtime must kill/remove the container if possible and return an empty timed-out result.
4. If the runtime completes normally, it must return raw stdout, stderr, and exit code.
5. The runtime must not infer whether a non-zero exit code means program error, infra error, OOM, or anything else.
6. The executor must be agnostic to language and task kind.
7. Accelerator requests are part of the contract surface even if a concrete runtime only partially supports them.

## Canonical examples

### Small Python run
```python
RunSpec(
    image="python:3.12-slim",
    command=("python", "-c", "print(2 + 2)"),
    limits=ResourceLimits(timeout_sec=30, memory="512m", cpus=1.0),
)
```

### Full-parameter run
```python
RunSpec(
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
```


## Supported today

- `RunSpec` as the single task description for one bounded container run
- `RawExecutionResult` as the raw execution contract
- Docker-backed runtime adapter
- forwarding of common Docker-relevant execution parameters without semantic interpretation

## Planned / out of scope for now

- real GPU / NPU binding semantics for `accelerators`
- queueing, retries, worker pools, and orchestration
- pass/fail semantics for tests, benchmarks, grading, or coverage tools
