"""审计日志持久化 + API 关键动作落审计的测试。

验证:
1. AuditLog 写 JSONL 文件, 每行带 timestamp/event/actor/action 字段
2. API: 提交任务(成功/失败)、审核、下载、越权尝试都产生审计事件
3. 事件按天归档 (audit-YYYYMMDD.jsonl)
"""
import json
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))
sys.path.insert(0, str(ROOT / "server2" / "audit"))

from audit_log import AuditLog  # noqa: E402
from geo_security.api import create_app  # noqa: E402
from geo_security.processing import ProcessingService  # noqa: E402


class FakeTrustMarkEngine:
    def embed(self, source: Path, destination: Path, watermark: int) -> int:
        destination.write_bytes(Path(source).read_bytes())
        return 1


@pytest.fixture()
def audit_env(tmp_path):
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    return audit_dir


def _make_app(tmp_path, audit_dir):
    workspace = tmp_path / "workspace"
    service = ProcessingService(workspace=workspace, key=b"test-key", trustmark_engine=FakeTrustMarkEngine())
    app = create_app(workspace=workspace, key=b"test-key",
                     allowed_input_roots=[tmp_path],
                     processing_service=service, audit_log_dir=audit_dir)
    return TestClient(app, headers={"X-Service-Token": "server1-local"})


def _read_events(audit_dir) -> list[dict]:
    today_file = audit_dir / f"audit-{date.today().isoformat()}.jsonl"
    if not today_file.exists():
        return []
    return [json.loads(line) for line in today_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_audit_log_writes_jsonl_with_required_fields(tmp_path):
    log = AuditLog(tmp_path)
    log.record("PROCESSING_STARTED", actor="tester", project_id="p1")
    events = json.loads((tmp_path / f"audit-{date.today().isoformat()}.jsonl").read_text(encoding="utf-8"))
    assert events["event"] == "PROCESSING_STARTED"
    assert events["actor"] == "tester"
    assert events["project_id"] == "p1"
    assert "timestamp" in events


def test_task_submit_success_records_audit(tmp_path, audit_env):
    client = _make_app(tmp_path, audit_env)
    source = tmp_path / "land.tif"
    source.write_bytes(b"\x00" * 4096)
    resp = client.post("/internal/tasks", json={
        "project_id": "p-audit", "user_id": "u1", "data_type": "GeoTIFF",
        "source_path": str(source), "watermark_text": "0xA5A5F00D",
    })
    assert resp.status_code == 202
    events = _read_events(audit_env)
    kinds = [e["event"] for e in events]
    assert "TASK_SUBMITTED" in kinds
    assert "TASK_COMPLETED" in kinds
    task = next(e for e in events if e["event"] == "TASK_COMPLETED")
    assert task["actor"] == "u1"
    assert task["project_id"] == "p-audit"
    assert task["data_type"] == "GeoTIFF"
    assert task["result_id"]


def test_task_submit_failure_and_approve_and_download_all_audited(tmp_path, audit_env):
    client = _make_app(tmp_path, audit_env)
    source = tmp_path / "bad.geojson"
    source.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
    resp = client.post("/internal/tasks", json={
        "project_id": "p-bad", "user_id": "u1", "data_type": "GeoJSON",
        "source_path": str(source), "watermark_text": "ok",
    })
    # genuine pre-processing rejection: 404 for missing input is not audited (probe
    # noise), but a 422 unsupported-type rejection is
    tif = tmp_path / "land.tif"
    tif.write_bytes(b"\x00" * 4096)
    resp = client.post("/internal/tasks", json={
        "project_id": "p-bad2", "user_id": "u2", "data_type": "LASER",
        "source_path": str(tif), "watermark_text": "0x1",
    })
    assert resp.status_code == 422
    events = _read_events(audit_env)
    assert any(e["event"] == "TASK_REJECTED" for e in events)

    # genuine processing failure: engine raises RuntimeError mid-embed
    from geo_security.api import create_app as _create_app

    class FailingEngine:
        def embed(self, source: Path, destination: Path, watermark: int) -> int:
            destination.write_bytes(b"partial")
            raise RuntimeError("watermark failed")

    ws = tmp_path / "ws-fail"
    svc = ProcessingService(ws, b"test-key", trustmark_engine=FailingEngine())
    fail_client = TestClient(_create_app(ws, b"test-key", allowed_input_roots=[tmp_path],
                                         processing_service=svc, audit_log_dir=audit_env),
                             headers={"X-Service-Token": "server1-local"})
    resp = fail_client.post("/internal/tasks", json={
        "project_id": "p-bad3", "user_id": "u3", "data_type": "GeoTIFF",
        "source_path": str(tif), "watermark_text": "0x1",
    })
    assert resp.status_code == 202
    assert resp.json()["status"] == "FAILED"
    events = _read_events(audit_env)
    assert any(e["event"] == "TASK_FAILED" for e in events)
    failed = next(e for e in events if e["event"] == "TASK_FAILED")
    assert failed["project_id"] == "p-bad3"

    # approve + manifest + download
    ok_source = tmp_path / "ok.geojson"
    ok_source.write_text('{"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"a": 1}, "geometry": null}]}', encoding="utf-8")
    resp = client.post("/internal/tasks", json={
        "project_id": "p-ok", "user_id": "u4", "data_type": "GeoJSON",
        "source_path": str(ok_source), "watermark_text": "ok",
    })
    result_id = resp.json()["result_id"]
    client.post(f"/internal/results/{result_id}/approve", json={"reviewer_id": "reviewer1"})
    client.get(f"/readonly/results/{result_id}/manifest", params={"user_id": "u4", "project_id": "p-ok"})
    events = _read_events(audit_env)
    kinds = [e["event"] for e in events]
    assert "RESULT_APPROVED" in kinds
    assert "RESULT_MANIFEST_READ" in kinds
    approved = next(e for e in events if e["event"] == "RESULT_APPROVED")
    assert approved["actor"] == "reviewer1"


def test_unauthorized_access_is_audited(tmp_path, audit_env):
    client = _make_app(tmp_path, audit_env)
    # no token
    bad = TestClient(client.app)
    resp = bad.post("/internal/tasks", json={
        "project_id": "p", "user_id": "u", "data_type": "GeoJSON",
        "source_path": str(tmp_path / "x.json"), "watermark_text": "ok",
    })
    assert resp.status_code == 401
    events = _read_events(audit_env)
    assert any(e["event"] == "AUTH_DENIED" for e in events)


def test_audit_file_is_per_day(tmp_path):
    log = AuditLog(tmp_path)
    log.record("A", actor="u")
    files = list(tmp_path.glob("audit-*.jsonl"))
    assert len(files) == 1
    assert files[0].name == f"audit-{date.today().isoformat()}.jsonl"
