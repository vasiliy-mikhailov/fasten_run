from __future__ import annotations

from .models import RawExecutionResult, RunSpec


class DockerRuntime:
    def __init__(self, client):
        self._client = client

    def run(self, task: RunSpec) -> RawExecutionResult:
        kwargs = {
            "image": task.image,
            "command": list(task.command),
            "detach": True,
            "remove": False,
            "network_disabled": not task.network_enabled,
            "environment": task.env,
        }

        if task.working_dir is not None:
            kwargs["working_dir"] = task.working_dir
        if task.limits.memory is not None:
            kwargs["mem_limit"] = task.limits.memory
        if task.limits.cpus is not None:
            kwargs["nano_cpus"] = int(task.limits.cpus * 1_000_000_000)
        if task.limits.pids_limit is not None:
            kwargs["pids_limit"] = task.limits.pids_limit
        if task.read_only_root_fs:
            kwargs["read_only"] = True
        if task.mounts:
            kwargs["volumes"] = {
                mount.source: {"bind": mount.target, "mode": "ro" if mount.read_only else "rw"}
                for mount in task.mounts
            }
        if task.user is not None:
            kwargs["user"] = task.user
        if task.name is not None:
            kwargs["name"] = task.name

        container = self._client.containers.run(**kwargs)

        try:
            container.wait(timeout=task.limits.timeout_sec)
        except Exception:
            try:
                container.kill()
            finally:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            return RawExecutionResult(
                timed_out=True,
                exit_code=None,
                stdout="",
                stderr="",
            )

        state = self._client.api.inspect_container(container.id)["State"]
        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
        exit_code = state.get("ExitCode")

        try:
            container.remove(force=True)
        except Exception:
            pass

        return RawExecutionResult(
            timed_out=False,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )
