"""server2 服务启动入口: 按部署配置装配 ProcessingService(TrustMark 引擎可选)、
审计日志目录和只读结果服务, 供 uvicorn 加载。

用法(部署机):
    set GDS_WORKSPACE=V:\geo_data_security
    set GEO_SECURITY_SERVER1_TOKEN=...
    set GDS_TRUSTMARK_PYTHON=...\trustmark_venv\Scripts\python.exe
    uvicorn geo_security.serve:app --host 0.0.0.0 --port 9081

只读输出端口可另起: uvicorn geo_security.serve:readonly_app --port 9082
(readonly_app 与主 app 共享同一 workspace 状态; 单进程部署时同 app 提供 /readonly/*)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .api import create_app

DEFAULT_WORKSPACE = Path(os.environ.get("GDS_WORKSPACE", "V:/geo_data_security"))
KEY_MATERIAL = os.environ.get("GDS_WORKSPACE_KEY", "local-prototype-key-material").encode()


def _trustmark_engine_or_none():
    """Build the TrustMark engine only when the isolated venv is reachable."""
    try:
        from .trustmark_engine import TrustMarkGeoTIFFEngine

        return TrustMarkGeoTIFFEngine()
    except Exception as exc:  # noqa: BLE001 - degrade to baseline watermarking
        print(f"TrustMark engine unavailable, falling back to baseline watermarking: {exc}", file=sys.stderr)
        return None


def _audit_dir() -> Path | None:
    configured = os.environ.get("GDS_AUDIT_DIR")
    if not configured:
        return None
    return Path(configured)


app = create_app(
    workspace=DEFAULT_WORKSPACE,
    key=KEY_MATERIAL,
    allowed_input_roots=[DEFAULT_WORKSPACE, Path(os.environ.get("GDS_INPUT_ROOT", DEFAULT_WORKSPACE))],
    processing_service=None,  # create_app builds one with workspace; engine injected below via env-only path
    audit_log_dir=_audit_dir(),
)

# Rebuild the processing service with the TrustMark engine when available. create_app
# accepted an injected service, so we patch the app state after construction.
from .processing import ProcessingService  # noqa: E402

_engine = _trustmark_engine_or_none()
_service = ProcessingService(workspace=DEFAULT_WORKSPACE, key=KEY_MATERIAL, trustmark_engine=_engine)
app.state.processing_service = _service
