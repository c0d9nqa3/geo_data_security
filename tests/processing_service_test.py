import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.processing import ProcessingService


def test_processing_service_dispatches_geojson_and_records_manifest(tmp_path):
    source = tmp_path / "source.geojson"
    source.write_text(json.dumps({
        "type": "Feature",
        "properties": {"name": "测试"},
        "geometry": {"type": "Point", "coordinates": [117.123456, 40.654321]},
    }), encoding="utf-8")
    service = ProcessingService(tmp_path / "workspace", b"service-key")

    artifact = service.process("project-1", "GeoJSON", source, user_id="user-1", timestamp="2026-01-01T00:00:00Z", decimals=3)

    assert artifact.status == "PENDING"
    output = Path(artifact.output)
    assert output.exists()
    manifest = json.loads((output.parent / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["project_id"] == "project-1"
    assert manifest["data_type"] == "GeoJSON"
    assert manifest["files_processed"] == 1


def test_processing_service_dispatches_geotiff_and_texture_directory(tmp_path):
    tif = tmp_path / "source.tif"
    values = np.arange(64 * 64, dtype=np.float32).reshape(64, 64)
    profile = {"driver": "GTiff", "height": 64, "width": 64, "count": 1, "dtype": "float32", "crs": "EPSG:4326", "transform": from_origin(117, 41, 0.01, 0.01)}
    with rasterio.open(tif, "w", **profile) as dataset:
        dataset.write(values, 1)
    texture_dir = tmp_path / "textures"
    texture_dir.mkdir()
    Image.fromarray(np.full((128, 128, 3), 128, dtype=np.uint8)).save(texture_dir / "a.png")
    service = ProcessingService(tmp_path / "workspace", b"service-key")

    geotiff_artifact = service.process("project-2", "GeoTIFF", tif, watermark=0x10203040)
    texture_artifact = service.process("project-2", "OSGB_TEXTURES", texture_dir, watermark=0x10203040)

    assert Path(geotiff_artifact.output).exists()
    assert Path(texture_artifact.output, "a.png").exists()
    assert json.loads((Path(geotiff_artifact.output).parent / "manifest.json").read_text())["data_type"] == "GeoTIFF"
    assert json.loads((Path(texture_artifact.output) / "manifest.json").read_text())["data_type"] == "OSGB_TEXTURES"
