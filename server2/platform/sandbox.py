from __future__ import annotations

import os
import subprocess
from pathlib import Path


class SandboxError(RuntimeError):
    pass


class WindowsProcessSandbox:
    """Conservative process runner boundary for the local prototype.

    This is not a security-certified sandbox. It enforces allow-listed executables,
    a project working directory and a timeout before the AppContainer adapter is
    integrated on the target server.
    """

    def __init__(self, allowed_executables: set[str]):
        self.allowed_executables = {os.path.basename(item).lower() for item in allowed_executables}

    def run(self, executable: Path | str, args: list[str], workdir: Path, timeout_seconds: int = 300) -> subprocess.CompletedProcess[str]:
        executable = Path(executable)
        if executable.name.lower() not in self.allowed_executables:
            raise SandboxError(f"executable is not allow-listed: {executable.name}")
        workdir = workdir.resolve()
        if not workdir.is_dir():
            raise SandboxError(f"workdir does not exist: {workdir}")
        try:
            return subprocess.run(
                [str(executable), *args],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxError("task timed out") from exc
        except subprocess.CalledProcessError as exc:
            raise SandboxError(exc.stderr.strip() or "task failed") from exc
