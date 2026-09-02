from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from .crypto import derive_key, encrypt_text
from .vector_watermark import embed_shapefile_watermark, extract_shapefile_watermark, geometry_digest, sha256_file


class OutputNotReadyError(RuntimeError):
    pass


class UnknownResultError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProcessingResult:
    result_id: str
    project_id: str
    files_processed: int
    watermark_field_count: int
    encrypted_watermark_count: int
    geometry_digest_before: str
    geometry_digest_after: str
    approval_status: str


class LocalProcessingPipeline:
    def __init__(self, root: Path, key: bytes):
        self.root = Path(root)
        self.key = key
        self.audit_events: list[dict] = []
        self.results: dict[str, dict] = {}

    def _event(self, event_type: str, **details: str) -> None:
        self.audit_events.append({"event_type": event_type, **details})

    def process_shapefile_dataset(self, project_id: str, source_dir: Path, user_id: str, watermark_text: str) -> ProcessingResult:
        source_dir = Path(source_dir)
        result_id = str(uuid.uuid4())
        project_root = self.root / "projects" / project_id
        input_dir = project_root / "input"
        result_dir = project_root / "results" / result_id
        input_dir.mkdir(parents=True, exist_ok=False)
        result_dir.mkdir(parents=True, exist_ok=False)
        self._event("PROCESSING_STARTED", project_id=project_id, result_id=result_id, user_id=user_id)
        source_shps = sorted(source_dir.glob("*.shp"))
        if not source_shps:
            raise ValueError("no shapefiles found")
        before = hashlib.sha256()
        after = hashlib.sha256()
        encrypted_count = 0
        for source in source_shps:
            copied = input_dir / source.name
            for sidecar in source.parent.glob(f"{source.stem}.*"):
                shutil.copy2(sidecar, input_dir / sidecar.name)
            before.update(geometry_digest(copied).encode())
            destination = result_dir / source.name
            embed_shapefile_watermark(copied, destination, watermark_text, self.key)
            for suffix in (".prj", ".cpg", ".sbn", ".sbx", ".shp.xml"):
                sidecar = input_dir / f"{source.stem}{suffix}"
                if sidecar.exists():
                    shutil.copy2(sidecar, result_dir / sidecar.name)
            after.update(geometry_digest(destination).encode())
            encrypted_count += len(extract_shapefile_watermark(destination, self.key))
        self._event("WATERMARK_EMBEDDED", project_id=project_id, result_id=result_id, user_id=user_id)
        result = ProcessingResult(result_id, project_id, len(source_shps), len(source_shps), encrypted_count, before.hexdigest(), after.hexdigest(), "PENDING")
        self.results[result_id] = {"result": result, "result_dir": result_dir, "user_id": user_id}
        self._event("PROCESSING_COMPLETED", project_id=project_id, result_id=result_id, user_id=user_id)
        return result

    def approve_result(self, result_id: str, reviewer_id: str) -> None:
        record = self.results.get(result_id)
        if not record:
            raise UnknownResultError(result_id)
        old = record["result"]
        record["result"] = ProcessingResult(old.result_id, old.project_id, old.files_processed, old.watermark_field_count, old.encrypted_watermark_count, old.geometry_digest_before, old.geometry_digest_after, "APPROVED")
        self._event("RESULT_APPROVED", result_id=result_id, reviewer_id=reviewer_id)

    def read_result(self, result_id: str, user_id: str, project_id: str) -> list[str]:
        record = self.results.get(result_id)
        if not record or record["result"].project_id != project_id or record["user_id"] != user_id:
            raise UnknownResultError(result_id)
        if record["result"].approval_status != "APPROVED":
            raise OutputNotReadyError(result_id)
        return [str(path) for path in sorted(record["result_dir"].glob("*.shp"))]
