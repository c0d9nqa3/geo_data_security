from __future__ import annotations

import subprocess
import time
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

    Mount/dismount use VeraCrypt's command line with the password passed on
    the command line; production deployments must read it from an approved
    secret store and review that this is acceptable on their baseline.
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

    def create_volume(self, volume_path: Path | str, size: str, password: str,
                      encryption: str = "AES", hash_algo: str = "SHA-512",
                      filesystem: str = "NTFS", fmt_executable: Path | str | None = None) -> CommandResult:
        """Create an encrypted volume. Requires elevation (UAC). Returns after format exits."""
        volume_path = Path(volume_path)
        volume_path.parent.mkdir(parents=True, exist_ok=True)
        fmt = Path(fmt_executable) if fmt_executable else Path(r"C:/Program Files/VeraCrypt/VeraCrypt Format.exe")
        if not fmt.exists():
            raise PlatformCommandError(f"VeraCrypt Format.exe not found: {fmt}")
        completed = subprocess.run(
            [str(fmt), "/create", str(volume_path), "/size", size,
             "/encryption", encryption, "/hash", hash_algo, "/filesystem", filesystem,
             "/password", password, "/silent"],
            capture_output=True, text=True, check=False,
        )
        result = CommandResult(completed.returncode, completed.stdout, completed.stderr)
        if result.returncode != 0:
            raise PlatformCommandError(result.stderr.strip() or result.stdout.strip() or "VeraCrypt volume creation failed")
        return result

    def mount_volume(self, volume_path: Path | str, letter: str, password: str, settle_seconds: float = 3.0) -> CommandResult:
        """Mount volume at drive letter. Ordinary-user mount works when the driver is installed."""
        result = self.run_approved_command(
            ["/volume", str(volume_path), "/letter", letter, "/password", password, "/quit", "/silent"]
        )
        time.sleep(settle_seconds)
        return result

    def dismount_volume(self, letter: str = "V") -> CommandResult:
        """Dismount a drive letter. Tolerates an already-dismounted letter."""
        if not self.available():
            raise PlatformCommandError(f"VeraCrypt executable not found: {self.executable}")
        completed = subprocess.run(
            [str(self.executable), "/dismount", letter, "/quit", "/silent"],
            capture_output=True, text=True, check=False,
        )
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)

    def is_mounted(self, letter: str = "V") -> bool:
        """True when the drive letter is an accessible directory (mount probe)."""
        probe = Path(f"{letter}:/")
        return probe.is_dir()
