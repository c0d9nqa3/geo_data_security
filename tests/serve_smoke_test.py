"""serve.py 装配冒烟: 模块可加载、引擎按环境装配、健康端点存在。"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))


def test_serve_module_assembles_app_and_injects_trustmark(tmp_path, monkeypatch):
    monkeypatch.setenv("GDS_WORKSPACE", str(tmp_path / "ws"))
    import importlib

    import geo_security.serve as serve
    importlib.reload(serve)
    assert serve.app is not None
    paths = {route.path for route in serve.app.routes}
    assert "/health" in paths
    assert "/internal/tasks" in paths
    service = serve.app.state.processing_service
    assert service is not None
    # engine present because the isolated venv is installed in this repo
    assert service.trustmark_engine is not None
    assert type(service.trustmark_engine).__name__ == "TrustMarkGeoTIFFEngine"
