from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from .crypto import encrypt_text
from .geojson_watermark import embed_geojson_watermark
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
    """统一处理 GeoJSON、GeoTIFF 和纹理目录，结果写入项目结果目录。"""

    def __init__(self, workspace: Path, key: bytes, trustmark_engine=None):
        self.workspace = Path(workspace)
        self.key = key
        self.trustmark_engine = trustmark_engine
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _artifact_dir(self, project_id: str) -> tuple[str, Path]:
        artifact_id = str(uuid.uuid4())
        output = self.workspace / "projects" / project_id / "results" / artifact_id
        output.mkdir(parents=True, exist_ok=False)
        return artifact_id, output

    def _failed(self, output_dir: Path) -> None:
        shutil.rmtree(output_dir, ignore_errors=True)

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

    def process_geojson(self, project_id: str, source: Path, user_id: str, timestamp: str, decimals: int | None = None) -> ProcessingArtifact:
        from .precision import reduce_geojson_precision

        source = Path(source)
        artifact_id, output_dir = self._artifact_dir(project_id)
        try:
            prepared = source
            if decimals is not None:
                prepared = output_dir / "precision_reduced.geojson"
                reduce_geojson_precision(source, prepared, decimals)
            destination = output_dir / "watermarked.geojson"
            count = embed_geojson_watermark(prepared, destination, f"{user_id}|{timestamp}", self.key)
            self._write_manifest(output_dir, project_id, artifact_id, "GeoJSON", source, destination, count)
            return ProcessingArtifact(artifact_id, "GeoJSON", str(source), str(destination), count, "PENDING")
        except Exception:
            self._failed(output_dir)
            raise

    def process_geotiff(self, project_id: str, source: Path, watermark: int) -> ProcessingArtifact:
        from .geotiff_watermark import embed_geotiff_watermark

        source = Path(source)
        artifact_id, output_dir = self._artifact_dir(project_id)
        try:
            destination = output_dir / "watermarked.tif"
            if self.trustmark_engine is not None:
                count = int(self.trustmark_engine.embed(source, destination, watermark))
            else:
                embed_geotiff_watermark(source, destination, watermark)
                count = 1
            self._write_manifest(output_dir, project_id, artifact_id, "GeoTIFF", source, destination, count)
            return ProcessingArtifact(artifact_id, "GeoTIFF", str(source), str(destination), count, "PENDING")
        except Exception:
            self._failed(output_dir)
            raise

    def process_texture_directory(self, project_id: str, source_dir: Path, watermark: int) -> ProcessingArtifact:
        source_dir = Path(source_dir)
        textures = sorted(path for path in source_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"}) if source_dir.is_dir() else []
        if not textures:
            raise ValueError("no JPG/PNG textures found")
        artifact_id, output_dir = self._artifact_dir(project_id)
        try:
            for source in textures:
                embed_texture_watermark(source, output_dir / source.name, watermark)
            self._write_manifest(output_dir, project_id, artifact_id, "OSGB_TEXTURES", source_dir, output_dir, len(textures))
            return ProcessingArtifact(artifact_id, "OSGB_TEXTURES", str(source_dir), str(output_dir), len(textures), "PENDING")
        except Exception:
            self._failed(output_dir)
            raise

    def process(self, project_id: str, data_type: str, source: Path, **kwargs) -> ProcessingArtifact:
        normalized = data_type.upper()
        if normalized in {"GEOJSON", "SHP"}:
            return self.process_geojson(project_id, source, kwargs["user_id"], kwargs["timestamp"], kwargs.get("decimals"))
        if normalized in {"GEOTIFF", "GTIFF"}:
            return self.process_geotiff(project_id, source, kwargs["watermark"])
        if normalized in {"OSGB_TEXTURES", "TEXTURES", "OSGB"}:
            return self.process_texture_directory(project_id, source, kwargs["watermark"])
        raise UnsupportedDataTypeError(f"no verified local handler for {data_type}")
