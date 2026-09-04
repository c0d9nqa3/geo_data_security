"""TaskStore persistence tests: state survives app reconstruction."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.api import create_app  # noqa: E402
from geo_security.processing import ProcessingService  # noqa: E402


def test_task_and_approval_survive_app_reconstruction(tmp_path):
    workspace = tmp_path / "workspace"
    source = tmp_path / "input.geojson"
    source.write_text('{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"id":1},"geometry":null}]}', encoding="utf-8")
    service = ProcessingService(workspace, b"test-key")

    app1 = create_app(workspace, b"test-key", allowed_input_roots=[tmp_path], processing_service=service)
    client1 = TestClient(app1, headers={"X-Service-Token": "server1-local"})
    created = client1.post("/internal/tasks", json={
        "project_id": "persisted-project", "user_id": "user1", "data_type": "GeoJSON",
        "source_path": str(source), "watermark_text": "unused",
    })
    assert created.status_code == 202
    body = created.json()
    result_id = body["result_id"]
    assert client1.post(f"/internal/results/{result_id}/approve", json={"reviewer_id": "reviewer"}).status_code == 200

    # New FastAPI app instance, same workspace/database, simulates process restart.
    app2 = create_app(workspace, b"test-key", allowed_input_roots=[tmp_path], processing_service=service)
    client2 = TestClient(app2, headers={"X-Service-Token": "server1-local"})
    status = client2.get(f"/internal/tasks/{body['task_id']}")
    assert status.status_code == 200
    assert status.json()["status"] == "COMPLETED"
    manifest = client2.get(f"/readonly/results/{result_id}/manifest", params={"user_id": "user1", "project_id": "persisted-project"})
    assert manifest.status_code == 200
    assert manifest.json()["status"] == "APPROVED"
