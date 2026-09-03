"""TrustMark 瓦片 GeoTIFF 引擎（主环境侧子进程桥）。

主项目 venv（numpy>=2）不能 import torch/trustmark，因此本引擎通过 subprocess
调用独立 trustmark venv 的 runner（`trustmark_geotiff_runner.py`）完成嵌入/提取。

runner 路径通过环境变量 GDS_TRUSTMARK_PYTHON / GDS_TRUSTMARK_RUNNER 配置，
便于部署到服务器时指向实际安装位置；缺省指向仓库 runtime/ 下独立 venv。
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


class TrustMarkEngineUnavailableError(RuntimeError):
    pass


def default_trustmark_python() -> str:
    configured = os.environ.get("GDS_TRUSTMARK_PYTHON")
    if configured:
        return configured
    repo_root = Path(__file__).resolve().parents[3]
    candidates = [
        repo_root / "runtime" / "trustmark_venv" / "Scripts" / "python.exe",
        repo_root / "runtime" / "trustmark_venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise TrustMarkEngineUnavailableError(
        "TrustMark venv python not found; set GDS_TRUSTMARK_PYTHON or create runtime/trustmark_venv"
    )


def default_runner_script() -> str:
    configured = os.environ.get("GDS_TRUSTMARK_RUNNER")
    if configured:
        return configured
    return str(Path(__file__).resolve().parent / "trustmark_geotiff_runner.py")


class TrustMarkGeoTIFFEngine:
    """Embed/extract GeoTIFF watermark by shelling out to the isolated TrustMark venv."""

    def __init__(self, python: str | None = None, runner: str | None = None, timeout: int = 1800):
        self.python = python or default_trustmark_python()
        self.runner = runner or default_runner_script()
        self.timeout = timeout
        if not Path(self.python).exists():
            raise TrustMarkEngineUnavailableError(f"trustmark python not found: {self.python}")
        if not Path(self.runner).exists():
            raise TrustMarkEngineUnavailableError(f"trustmark runner not found: {self.runner}")

    def _call(self, arguments: list[str]) -> dict:
        command = [self.python, self.runner, *arguments]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"TrustMark runner timed out after {self.timeout}s: {command}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"TrustMark runner failed (exit {completed.returncode}): {detail}")
        try:
            return json.loads(completed.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError) as exc:
            raise RuntimeError(f"TrustMark runner returned non-JSON output: {completed.stdout!r}") from exc

    def embed(self, source: Path, destination: Path, watermark: int) -> int:
        if not 0 <= watermark <= 0xFFFFFFFF:
            raise ValueError("watermark must be an unsigned 32-bit integer")
        result = self._call(["embed", str(source), str(destination), format(watermark, "08X")])
        if "error" in result:
            raise RuntimeError(f"TrustMark embed failed: {result['error']}")
        return int(result.get("tiles", 1))

    def extract(self, source: Path, watermark: int) -> dict:
        result = self._call(["extract", str(source), format(watermark, "08X")])
        if "error" in result:
            raise RuntimeError(f"TrustMark extract failed: {result['error']}")
        return result
