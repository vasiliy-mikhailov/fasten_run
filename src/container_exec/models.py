from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class AcceleratorSpec:
    kind: str
    count: Optional[int] = None
    device_ids: tuple[str, ...] = ()
    vendor: Optional[str] = None
    memory: Optional[str] = None
    exclusive: bool = False


@dataclass(frozen=True)
class MountSpec:
    source: str
    target: str
    read_only: bool = True


@dataclass(frozen=True)
class ResourceLimits:
    timeout_sec: int = 30
    cpus: Optional[float] = 1.0
    memory: Optional[str] = "512m"
    pids_limit: Optional[int] = None


@dataclass(frozen=True)
class RunSpec:
    image: str
    command: tuple[str, ...]
    env: dict[str, str] = field(default_factory=dict)
    working_dir: Optional[str] = None
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    network_enabled: bool = False
    read_only_root_fs: bool = False
    mounts: tuple[MountSpec, ...] = ()
    accelerators: tuple[AcceleratorSpec, ...] = ()
    user: Optional[str] = None
    name: Optional[str] = None


# Backward-compatible alias while the public API transitions to RunSpec.
ContainerTask = RunSpec


@dataclass(frozen=True)
class RawExecutionResult:
    timed_out: bool
    exit_code: int | None
    stdout: str
    stderr: str
