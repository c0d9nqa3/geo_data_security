"""TrustMark 真实引擎接入 ProcessingService / API 的端到端测试。

依赖 runtime/trustmark_venv 存在（含 torch 2.1.2+cpu、trustmark 模型）。环境不存在时跳过，
避免 CI/未部署机器上误报失败。
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

TRUSTMARK_PYTHON = ROOT / "runtime" / "trustmark_venv" / "Scripts" / "python.exe"
TRUSTMARK_RUNNER = ROOT / "server2" / "pipeline" / "geo_security" / "trustmark_geotiff_runner.py"
HAS_TRUSTMARK_ENV = TRUSTMARK_PYTHON.exists() and TRUSTMARK_RUNNER.exists()

pytestmark = pytest.mark.skipif(not HAS_TRUSTMARK_ENV, reason="TrustMark isolated venv not present")


@pytest.fixture()
def real_engine():
    from geo_security.trustmark_engine import TrustMarkGeoTIFFEngine

    engine = TrustMarkGeoTIFFEngine(python=str(TRUSTMARK_PYTHON), runner=str(TRUSTMARK_RUNNER), timeout=1800)
    return engine


def _make_geotiff(path: Path, size: int = 128) -> None:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    rng = np.random.default_rng(11)
    values = rng.integers(0, 256, (size, size), dtype=np.uint8)
    profile = {
        "driver": "GTiff", "height": size, "width": size, "count": 1, "dtype": "uint8",
        "crs": "EPSG:32644", "transform": from_origin(500000, 4000000, 30, 30),
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(values, 1)
        ds.update_tags(AREA_OR_POINT="Area")


def test_trustmark_engine_embeds_and_extracts_synthetic(tmp_path, real_engine):
    source = tmp_path / "src.tif"
    destination = tmp_path / "marked.tif"
    _make_geotiff(source, size=1024)
    tiles = real_engine.embed(source, destination, 0x1234ABCD)
    assert tiles >= 1
    import rasterio
    with rasterio.open(destination) as ds:
        assert ds.dtypes[0] == "uint8"
        assert ds.crs == "EPSG:32644"
        assert ds.tags().get("GDS_TM_ENGINE", "").startswith("TrustMark")
    result = real_engine.extract(destination, 0x1234ABCD)
    assert result["detected"] is True


def test_processing_service_routes_geotiff_through_trustmark(tmp_path, real_engine):
    from geo_security.processing import ProcessingService

    source = tmp_path / "src.tif"
    _make_geotiff(source, size=1024)
    service = ProcessingService(tmp_path / "workspace", b"key", trustmark_engine=real_engine)
    artifact = service.process("project-1", "GeoTIFF", source, watermark=0xA5A5F00D)
    assert Path(artifact.output).exists()
    manifest = json.loads((Path(artifact.output).parent / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["data_type"] == "GeoTIFF"
    assert manifest["files_processed"] >= 1


def test_api_task_with_trustmark_engine_completes_end_to_end(tmp_path, real_engine):
    from fastapi.testclient import TestClient
    from geo_security.api import create_app
    from geo_security.processing import ProcessingService

    source = tmp_path / "src.tif"
    _make_geotiff(source, size=1024)
    service = ProcessingService(tmp_path / "workspace", b"key", trustmark_engine=real_engine)
    app = create_app(tmp_path / "workspace", b"key", allowed_input_roots=[tmp_path], processing_service=service)
    client = TestClient(app)

    response = client.post("/internal/tasks", json={
        "project_id": "p1", "user_id": "u1", "data_type": "GeoTIFF",
        "source_path": str(source), "watermark_text": "0xA5A5F00D",
    }, headers={"X-Service-Token": "server1-local"})
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "COMPLETED", body
    result_id = body["result_id"]
    approved = client.post(f"/internal/results/{result_id}/approve", json={"reviewer_id": "r1"}, headers={"X-Service-Token": "server1-local"})
    assert approved.status_code == 200
    downloaded = client.get(f"/readonly/results/{result_id}/file", params={"user_id": "u1", "project_id": "p1", "filename": "watermarked.tif"})
    assert downloaded.status_code == 200
    assert len(downloaded.content) > 0
