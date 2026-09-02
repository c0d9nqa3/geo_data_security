import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from fastapi.testclient import TestClient

from geo_security.api import create_app


def test_internal_task_submission_status_and_approval(tmp_path):
    source = tmp_path / "source.geojson"
    source.write_text(json.dumps({
        "type": "Feature",
        "properties": {"name": "A"},
        "geometry": {"type": "Point", "coordinates": [117.123456, 40.654321]},
    }), encoding="utf-8")
    app = create_app(tmp_path / "workspace", b"task-key", allowed_input_roots=[tmp_path])
    client = TestClient(app)

    response = client.post("/internal/tasks", json={
        "project_id": "project-1",
        "user_id": "user-1",
        "data_type": "GeoJSON",
        "source_path": str(source),
        "watermark_text": "user-1|project-1",
        "precision_decimals": 3,
    }, headers={"X-Service-Token": "server1-local"})
    assert response.status_code == 202
    task_id = response.json()["task_id"]

    status = client.get(f"/internal/tasks/{task_id}", headers={"X-Service-Token": "server1-local"})
    assert status.status_code == 200
    assert status.json()["task_id"] == task_id
    assert status.json()["status"] == "COMPLETED"
    result_id = status.json()["result_id"]

    pending = client.get(f"/readonly/results/{result_id}/manifest", params={"user_id": "user-1", "project_id": "project-1"})
    assert pending.status_code == 403

    approved = client.post(f"/internal/results/{result_id}/approve", json={"reviewer_id": "reviewer-1"}, headers={"X-Service-Token": "server1-local"})
    assert approved.status_code == 200
    manifest = client.get(f"/readonly/results/{result_id}/manifest", params={"user_id": "user-1", "project_id": "project-1"})
    assert manifest.status_code == 200
    assert manifest.json()["data_type"] == "GeoJSON"


def test_internal_tasks_require_service_token_and_reject_outside_input_root(tmp_path):
    source = tmp_path / "source.geojson"
    source.write_text('{"type":"Feature","properties":{},"geometry":null}', encoding="utf-8")
    app = create_app(tmp_path / "workspace", b"task-key", allowed_input_roots=[tmp_path / "allowed"])
    client = TestClient(app)

    assert client.post("/internal/tasks", json={}).status_code == 401
    response = client.post("/internal/tasks", json={
        "project_id": "project-1", "user_id": "user-1", "data_type": "GeoJSON", "source_path": str(source), "watermark_text": "x"
    }, headers={"X-Service-Token": "server1-local"})
    assert response.status_code == 403
