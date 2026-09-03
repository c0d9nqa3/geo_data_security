"""SHP 目录(DLG) 经 /internal/tasks 全链 e2e: 提交→完成→审核→manifest→下载。

验证:
1. SHP 目录(多 .shp 层)提交 -> 202 COMPLETED
2. 审核后 manifest/output 指向结果目录
3. 下载的 .shp 可提取出加密水印且几何不变
"""
import json
import shutil
import sys
from pathlib import Path

import shapefile
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.api import create_app  # noqa: E402
from geo_security.processing import ProcessingService  # noqa: E402
from geo_security.vector_watermark import (  # noqa: E402
    embed_shapefile_watermark,
    extract_shapefile_watermark,
    geometry_digest,
)

KEY = b"test-shp-key"
WATERMARK_TEXT = "e2e-shp-20260904"


def _make_layer(dir_path: Path, name: str, count: int = 10) -> Path:
    w = shapefile.Writer(str(dir_path / name), shapeType=shapefile.POINT)
    w.field("name", "C")
    for i in range(count):
        w.point(i * 0.01, i * 0.02)
        w.record(f"pt-{i}")
    w.close()
    (dir_path / f"{name}.prj").write_text('GEOGCS["WGS 84",DATUM["WGS_1984"],SPHEROID["WGS 84",6378137,298.257223563],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]', encoding="utf-8")
    return dir_path / f"{name}.shp"


def test_shp_directory_full_chain(tmp_path):
    workspace = tmp_path / "workspace"
    service = ProcessingService(workspace=workspace, key=KEY)
    app = create_app(workspace=workspace, key=KEY, allowed_input_roots=[tmp_path], processing_service=service)
    client = TestClient(app, headers={"X-Service-Token": "server1-local"})

    dlg = tmp_path / "dlg_input"
    dlg.mkdir()
    layer_a = _make_layer(dlg, "roads")
    layer_b = _make_layer(dlg, "river")
    before_a = geometry_digest(layer_a)

    resp = client.post("/internal/tasks", json={
        "project_id": "p-shp", "user_id": "user-dlg", "data_type": "SHP",
        "source_path": str(dlg), "watermark_text": WATERMARK_TEXT,
    })
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "COMPLETED"
    result_id = body["result_id"]

    # approve as reviewer, then fetch manifest as the requesting user
    appr = client.post(f"/internal/results/{result_id}/approve", json={"reviewer_id": "reviewer-1"})
    assert appr.status_code == 200
    manifest = client.get(f"/readonly/results/{result_id}/manifest", params={"user_id": "user-dlg", "project_id": "p-shp"})
    assert manifest.status_code == 200
    data = manifest.json()
    assert data["data_type"] == "SHP"
    assert data["files_processed"] == 2

    # download a layer, verify watermark extractable and geometry unchanged
    dl = client.get(f"/readonly/results/{result_id}/file", params={"user_id": "user-dlg", "project_id": "p-shp", "filename": "roads.shp"})
    assert dl.status_code == 200
    out = tmp_path / "downloaded"
    out.mkdir()
    (out / "roads.shp").write_bytes(dl.content)
    # fetch the .dbf sidecar too so pyshp can read records
    dl_dbf = client.get(f"/readonly/results/{result_id}/file", params={"user_id": "user-dlg", "project_id": "p-shp", "filename": "roads.dbf"})
    (out / "roads.dbf").write_bytes(dl_dbf.content)
    dl_prj = client.get(f"/readonly/results/{result_id}/file", params={"user_id": "user-dlg", "project_id": "p-shp", "filename": "roads.prj"})
    (out / "roads.prj").write_bytes(dl_prj.content)

    texts = extract_shapefile_watermark(out / "roads.shp", KEY)
    assert texts and all(t == WATERMARK_TEXT for t in texts)
    assert geometry_digest(out / "roads.shp") == before_a
    # source sidecar untouched in original tree
    assert (dlg / "roads.prj").exists()
    shutil.rmtree(dlg, ignore_errors=True)


def test_shp_directory_empty_rejected(tmp_path):
    workspace = tmp_path / "workspace"
    service = ProcessingService(workspace=workspace, key=KEY)
    app = create_app(workspace=workspace, key=KEY, allowed_input_roots=[tmp_path], processing_service=service)
    client = TestClient(app, headers={"X-Service-Token": "server1-local"})
    empty = tmp_path / "empty_dir"
    empty.mkdir()
    resp = client.post("/internal/tasks", json={
        "project_id": "p-empty", "user_id": "u", "data_type": "SHP",
        "source_path": str(empty), "watermark_text": "x",
    })
    assert resp.status_code == 422  # empty input dir is a rejected task, same as empty textures
    shutil.rmtree(empty, ignore_errors=True)
