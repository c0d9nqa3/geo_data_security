from __future__ import annotations

import platform
import subprocess
from pathlib import Path


class SysmonAdapter:
    def __init__(self, executable: Path | str):
        self.executable = Path(executable)

    def installed(self) -> bool:
        return self.executable.exists()

    def install(self, config: Path) -> subprocess.CompletedProcess[str]:
        if not self.installed():
            raise FileNotFoundError(self.executable)
        if platform.system() != "Windows":
            raise RuntimeError("Sysmon installation requires Windows")
        return subprocess.run(
            [str(self.executable), "-accepteula", "-i", str(config)],
            capture_output=True,
            text=True,
            check=False,
        )
