from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from .crypto import encrypt_text
from .geojson_watermark import embed_geojson_watermark
from .geotiff_watermark import embed_geotiff_watermark
from .precision import reduce_geojson_precision
from .texture_watermark import embed_texture_watermark
from .vector_watermark import sha256_file


class UnsupportedDataTypeError(ValueError):
    pass


@dataclass(frozen=True)
class ProcessingArtifact:
    artifact_id: str
    data_type: str
    source: str
    output: str
    files_processed: int
    status: str


class ProcessingService:
    """Dispatches the verified data-type handlers used by the local loop."""

    def __init__(self, workspace: Path, key: bytes):
        self.workspace = Path(workspace)
        self.key = key
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _artifact_dir(self, project_id: str) -> tuple[str, Path]:
        artifact_id = str(uuid.uuid4())
        output = self.workspace / "projects" / project_id / "results" / artifact_id
        output.mkdir(parents=True, exist_ok=False)
        return artifact_id, output

    def process_geojson(self, project_id: str, source: Path, user_id: str, timestamp: str, decimals: int | None = None) -> ProcessingArtifact:
        artifact_id, output_dir = self._artifact_dir(project_id)
        prepared = output_dir / "prepared.geojson"
        if decimals is not None:
            reduced = output_dir / "precision_reduced.geojson"
            reduce_geojson_precision(Path(source), reduced, decimals)
            prepared = reduced
        destination = output_dir / "watermarked.geojson"
        count = embed_geojson_watermark(prepared if prepared.exists() else Path(source), destination, f"{user_id}|{timestamp}", self.key)
        self._write_manifest(output_dir, project_id, artifact_id, "GeoJSON", source, destination, count)
        return ProcessingArtifact(artifact_id, "GeoJSON", str(source), str(destination), count, "PENDING")

    def process_geotiff(self, project_id: str, source: Path, watermark: int) -> ProcessingArtifact:
        artifact_id, output_dir = self._artifact_dir(project_id)
        destination = output_dir / "watermarked.tif"
        embed_geotiff_watermark(Path(source), destination, watermark)
        self._write_manifest(output_dir, project_id, artifact_id, "GeoTIFF", source, destination, 1)
        return ProcessingArtifact(artifact_id, "GeoTIFF", str(source), str(destination), 1, "PENDING")

    def process_texture_directory(self, project_id: str, source_dir: Path, watermark: int) -> ProcessingArtifact:
        source_dir = Path(source_dir)
        if not source_dir.is_dir():
            raise ValueError("texture directory does not exist")
        textures = sorted(path for path in source_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"})
        if not textures:
            raise ValueError("no JPG/PNG textures found")
        artifact_id, output_dir = self._artifact_dir(project_id)
        for source in textures:
            destination = output_dir / source.name
            embed_texture_watermark(source, destination, watermark)
        self._write_manifest(output_dir, project_id, artifact_id, "OSGB_TEXTURES", source_dir, output_dir, len(textures))
        return ProcessingArtifact(artifact_id, "OSGB_TEXTURES", str(source_dir), str(output_dir), len(textures), "PENDING")

    def process(self, project_id: str, data_type: str, source: Path, **kwargs) -> ProcessingArtifact:
        normalized = data_type.upper()
        if normalized == "GEOJSON":
            return self.process_geojson(project_id, source, kwargs["user_id"], kwargs["timestamp"], kwargs.get("decimals"))
        if normalized == "GEOTIFF":
            return self.process_geotiff(project_id, source, kwargs["watermark"])
        if normalized in {"OSGB_TEXTURES", "TEXTURES"}:
            return self.process_texture_directory(project_id, source, kwargs["watermark"])
        raise UnsupportedDataTypeError(f"no verified local handler for {data_type}")

    @staticmethod
    def _write_manifest(output_dir: Path, project_id: str, artifact_id: str, data_type: str, source: Path, output: Path, count: int) -> None:
        manifest = {
            "artifact_id": artifact_id,
            "project_id": project_id,
            "data_type": data_type,
            "source": str(source),
            "output": str(output),
            "files_processed": count,
            "source_hash": sha256_file(source) if Path(source).is_file() else None,
            "status": "PENDING",
        }
        (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
