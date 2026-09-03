import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.api import create_app
from geo_security.processing import ProcessingService


class FakeTrustMarkEngine:
    def embed(self, source: Path, destination: Path, watermark: int) -> int:
        destination.write_bytes(Path(source).read_bytes())
        return 1


def _request(source: Path, data_type: str, **extra):
    payload = {
        "project_id": "p1",
        "user_id": "u1",
        "data_type": data_type,
        "source_path": str(source),
        "watermark_text": "0xA5A5F00D",
        **extra,
    }
    return payload


def _approve_and_download(client: TestClient, result_id: str, filename: str):
    approved = client.post(
        f"/internal/results/{result_id}/approve",
        json={"reviewer_id": "reviewer-1"},
        headers={"X-Service-Token": "server1-local"},
    )
    assert approved.status_code == 200
    downloaded = client.get(
        f"/readonly/results/{result_id}/file",
        params={"user_id": "u1", "project_id": "p1", "filename": filename},
    )
    assert downloaded.status_code == 200
    return downloaded


def test_internal_task_dispatches_geojson_geotiff_and_texture(tmp_path):
    geojson = tmp_path / "source.geojson"
    geojson.write_text(json.dumps({
        "type": "Feature",
        "properties": {"name": "A"},
        "geometry": {"type": "Point", "coordinates": [117.123456, 40.654321]},
    }), encoding="utf-8")
    geotiff = tmp_path / "source.tif"
    geotiff.write_bytes(b"fake-geotiff")
    texture_dir = tmp_path / "textures"
    texture_dir.mkdir()
    from PIL import Image
    Image.new("RGB", (64, 64), (120, 80, 40)).save(texture_dir / "a.png")

    service = ProcessingService(tmp_path / "workspace", b"key", trustmark_engine=FakeTrustMarkEngine())
    app = create_app(tmp_path / "workspace", b"key", allowed_input_roots=[tmp_path], processing_service=service)
    client = TestClient(app)

    cases = [
        (geojson, "GeoJSON", "watermarked.geojson"),
        (geotiff, "GeoTIFF", "watermarked.tif"),
        (texture_dir, "TEXTURES", "a.png"),
    ]
    for source, data_type, filename in cases:
        response = client.post("/internal/tasks", json=_request(source, data_type), headers={"X-Service-Token": "server1-local"})
        assert response.status_code == 202, response.text
        body = response.json()
        assert body["status"] == "COMPLETED"
        task_id = body["task_id"]
        status = client.get(f"/internal/tasks/{task_id}", headers={"X-Service-Token": "server1-local"})
        assert status.status_code == 200
        result_id = status.json()["result_id"]
        assert client.get(
            f"/readonly/results/{result_id}/manifest",
            params={"user_id": "u1", "project_id": "p1"},
        ).status_code == 403
        downloaded = _approve_and_download(client, result_id, filename)
        assert downloaded.content


def test_failed_task_is_marked_failed_and_result_directory_is_removed(tmp_path):
    source = tmp_path / "bad.tif"
    source.write_bytes(b"bad")

    class FailingEngine:
        def embed(self, source: Path, destination: Path, watermark: int) -> int:
            destination.write_bytes(b"partial")
            raise RuntimeError("watermark failed")

    service = ProcessingService(tmp_path / "workspace", b"key", trustmark_engine=FailingEngine())
    app = create_app(tmp_path / "workspace", b"key", allowed_input_roots=[tmp_path], processing_service=service)
    client = TestClient(app)
    response = client.post("/internal/tasks", json=_request(source, "GeoTIFF"), headers={"X-Service-Token": "server1-local"})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "FAILED"
    status = client.get(f"/internal/tasks/{body['task_id']}", headers={"X-Service-Token": "server1-local"})
    assert status.json()["status"] == "FAILED"
    assert not list((tmp_path / "workspace" / "projects" / "p1" / "results").glob("*"))
