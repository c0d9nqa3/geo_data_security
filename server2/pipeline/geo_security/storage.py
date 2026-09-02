from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .crypto import derive_key


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_project_path(root: Path, project_id: str, *parts: str) -> Path:
    if not project_id or project_id in {".", ".."} or any(ch in project_id for ch in "/\\"):
        raise ValueError("invalid project id")
    base = (Path(root) / "projects" / project_id).resolve()
    target = (base.joinpath(*parts)).resolve()
    if target != base and base not in target.parents:
        raise ValueError("path escapes project workspace")
    return target


class LocalWorkspace:
    """Local application workspace used before a real VeraCrypt volume is mounted."""

    def __init__(self, root: Path, key_material: bytes):
        self.root = Path(root)
        self.key = derive_key(key_material)

    def project_dir(self, project_id: str) -> Path:
        path = safe_project_path(self.root, project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def copy_package(self, project_id: str, source: Path, package_name: str = "input") -> Path:
        destination = safe_project_path(self.root, project_id, package_name)
        destination.mkdir(parents=True, exist_ok=False)
        source = Path(source).resolve()
        if not source.is_dir():
            raise ValueError("input package must be a directory")
        for item in source.iterdir():
            if item.is_file():
                shutil.copy2(item, destination / item.name)
        return destination

    def write_manifest(self, project_id: str, manifest: dict) -> Path:
        destination = safe_project_path(self.root, project_id, "manifest.json")
        destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return destination

    def cleanup_project(self, project_id: str) -> None:
        project = safe_project_path(self.root, project_id)
        if project.exists():
            shutil.rmtree(project)
