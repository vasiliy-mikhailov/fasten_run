from container_exec.models import AcceleratorSpec, MountSpec, ResourceLimits, RunSpec
from examples.use_cases import (
    ALL_PARAMETERS_RUNSPEC,
    ARBITRARY_SHELL_RUNSPEC,
    CODE_GRADING_RUNSPEC,
    COMPILE_VERIFICATION_RUNSPEC,
    COVERAGE_JSON_RUNSPEC,
    FORMATTING_CHECK_RUNSPEC,
    GENERATED_PATCH_VALIDATION_RUNSPEC,
    LINT_RUNSPEC,
    PYTEST_RUNSPEC,
    PYTHON_VALUE_RUNSPEC,
    REGRESSION_REPLAY_RUNSPEC,
    REPEATED_BENCHMARK_RUNSPEC,
    RUST_COMPILE_AND_RUN_RUNSPEC,
    SANDBOXED_FAILURE_REPRODUCTION_RUNSPEC,
)


def test_examples_are_runspecs() -> None:
    examples = [
        PYTHON_VALUE_RUNSPEC,
        RUST_COMPILE_AND_RUN_RUNSPEC,
        PYTEST_RUNSPEC,
        COVERAGE_JSON_RUNSPEC,
        ARBITRARY_SHELL_RUNSPEC,
        COMPILE_VERIFICATION_RUNSPEC,
        LINT_RUNSPEC,
        FORMATTING_CHECK_RUNSPEC,
        REPEATED_BENCHMARK_RUNSPEC,
        CODE_GRADING_RUNSPEC,
        REGRESSION_REPLAY_RUNSPEC,
        GENERATED_PATCH_VALIDATION_RUNSPEC,
        SANDBOXED_FAILURE_REPRODUCTION_RUNSPEC,
        ALL_PARAMETERS_RUNSPEC,
    ]

    assert all(isinstance(task, RunSpec) for task in examples)
    assert PYTHON_VALUE_RUNSPEC.command[0] == "python"
    assert RUST_COMPILE_AND_RUN_RUNSPEC.image.startswith("rust:")
    assert "pytest" in GENERATED_PATCH_VALIDATION_RUNSPEC.command[-1]


def test_all_parameters_runspec_uses_every_field() -> None:
    run = ALL_PARAMETERS_RUNSPEC

    assert run.image == "my-inference-image:latest"
    assert run.command == ("python", "score.py", "--batch", "32")
    assert run.env["MODEL_PATH"] == "/models/model.bin"
    assert run.working_dir == "/workspace"
    assert run.limits == ResourceLimits(timeout_sec=90, memory="4g", cpus=2.0, pids_limit=256)
    assert run.network_enabled is False
    assert run.read_only_root_fs is True
    assert run.mounts == (
        MountSpec(source="./workspace", target="/workspace", read_only=False),
        MountSpec(source="./models", target="/models", read_only=True),
    )
    assert run.accelerators == (
        AcceleratorSpec(kind="gpu", count=1, exclusive=True),
        AcceleratorSpec(kind="npu", device_ids=("npu0",), vendor="intel"),
    )
    assert run.user == "1000:1000"
    assert run.name == "llm-score-run"
