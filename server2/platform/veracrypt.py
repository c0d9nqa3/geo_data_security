from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


class PlatformCommandError(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class VeraCryptAdapter:
    """Windows VeraCrypt boundary.

    The prototype intentionally does not automate password entry. A deployment
    integration must use an approved secret mechanism and an administrator-
    reviewed command line after verifying the installed VeraCrypt version.
    """

    def __init__(self, executable: Path | str = Path(r"C:/Program Files/VeraCrypt/VeraCrypt.exe")):
        self.executable = Path(executable)

    def available(self) -> bool:
        return self.executable.exists()

    def help(self) -> CommandResult:
        if not self.available():
            raise PlatformCommandError(f"VeraCrypt executable not found: {self.executable}")
        completed = subprocess.run([str(self.executable), "/?"], capture_output=True, text=True, check=False)
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)

    def run_approved_command(self, args: Sequence[str]) -> CommandResult:
        """Run a deployment-approved command without logging its arguments."""
        if not self.available():
            raise PlatformCommandError(f"VeraCrypt executable not found: {self.executable}")
        completed = subprocess.run([str(self.executable), *args], capture_output=True, text=True, check=False)
        result = CommandResult(completed.returncode, completed.stdout, completed.stderr)
        if result.returncode != 0:
            raise PlatformCommandError(result.stderr.strip() or result.stdout.strip() or "VeraCrypt command failed")
        return result
