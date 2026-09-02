import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.api import create_app


def test_server2_api_exposes_health_and_readonly_result_flow(tmp_path):
    app = create_app(tmp_path / "workspace", b"api-test-key")
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok", "role": "processing_storage_readonly_output"}

    response = client.get(
        "/readonly/results/does-not-exist/manifest",
        params={"user_id": "user-1", "project_id": "project-1"},
    )
    assert response.status_code == 404


def test_server2_readonly_api_rejects_upload_and_unapproved_result(tmp_path):
    app = create_app(tmp_path / "workspace", b"api-test-key")
    client = TestClient(app)

    assert client.post("/readonly/results", json={"anything": "not allowed"}).status_code == 404
    assert client.get("/readonly/results/result-1/file", params={"user_id": "u", "project_id": "p", "filename": "x"}).status_code == 404
