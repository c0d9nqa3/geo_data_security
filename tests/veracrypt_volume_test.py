"""VeraCrypt 真实卷生命周期管理 + LocalWorkspace 加密存储闭环测试。

前置条件（满足才执行，否则跳过）：
- 测试卷存在: C:\\Users\\Steven\\geo_vc_test\\test_vc_volume.hc
- 卷密码在环境变量 GDS_TEST_VC_PASSWORD（或回退本文件同目录 secret 文件，不入库）

验证点：
1. mount_volume 把真实卷挂载到 V:
2. LocalWorkspace(root=V:/geo_data_security) 上 ProcessingService 处理真实任务
3. 结果落盘在加密卷内（NTFS 卷），卸载后重新挂载数据仍在（持久化）
"""
import os
import shutil
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))
sys.path.insert(0, str(ROOT / "server2" / "platform"))

from geo_security.processing import ProcessingService  # noqa: E402
from veracrypt import VeraCryptAdapter  # noqa: E402

VOLUME = Path(r"C:\Users\Steven\geo_vc_test\test_vc_volume.hc")
MOUNT_ROOT = Path("V:/geo_data_security")
PASSWORD = os.environ.get("GDS_TEST_VC_PASSWORD")
if not PASSWORD:
    secret_file = VOLUME.parent / "vc_password.txt"
    if secret_file.exists():
        PASSWORD = secret_file.read_text(encoding="utf-8").strip()
HAVE_VOLUME = VOLUME.exists() and PASSWORD is not None


def _mount_via_adapter(password: str) -> None:
    """Mount via VeraCryptAdapter. Ordinary-user mount needs no elevation when driver is present."""
    adapter = VeraCryptAdapter()
    adapter.mount_volume(VOLUME, "V", password)
    assert adapter.is_mounted("V"), "V: did not come up after mount"


def _dismount() -> None:
    VeraCryptAdapter().dismount_volume("V")


@pytest.mark.skipif(not HAVE_VOLUME, reason="VeraCrypt test volume not present")
class TestVeraCryptRealVolume:
    def setup_method(self):
        _dismount()
        time.sleep(3)  # driver needs a moment to release the drive letter
        if MOUNT_ROOT.exists() and not any(MOUNT_ROOT.iterdir()):
            shutil.rmtree(MOUNT_ROOT, ignore_errors=True)
        _mount_via_adapter(PASSWORD)
        time.sleep(2)

    def teardown_method(self):
        _dismount()

    def test_adapter_reports_volume_available(self):
        adapter = VeraCryptAdapter()
        assert adapter.available()
        assert adapter.is_mounted("V"), "setup_method should have mounted V:"

    def test_workspace_on_encrypted_volume_persists_across_remount(self):
        assert MOUNT_ROOT.is_dir(), "V:/geo_data_security not mounted"
        # write marker via LocalWorkspace-shaped layout
        projects = MOUNT_ROOT / "projects"
        projects.mkdir(parents=True, exist_ok=True)
        marker = projects / "persistence_probe.txt"
        marker.write_text("encrypted-persistence-check", encoding="utf-8")
        _dismount()
        time.sleep(3)
        _mount_via_adapter(PASSWORD)
        time.sleep(2)
        assert (projects / "persistence_probe.txt").read_text(encoding="utf-8") == "encrypted-persistence-check"

    def test_processing_service_task_on_encrypted_volume(self):
        workspace_root = MOUNT_ROOT
        service = ProcessingService(workspace=workspace_root, key=b"test-service-key-not-production")
        project_id = "vc-e2e-probe"
        (workspace_root / "projects" / project_id).mkdir(parents=True, exist_ok=True)
        package = workspace_root / "projects" / project_id / "input"
        package.mkdir(exist_ok=True)
        (package / "attr.json").write_text('{"name": "probe", "type": "FeatureCollection", "features": []}', encoding="utf-8")
        artifact = service.process(project_id, "GeoJSON", package / "attr.json", user_id="tester", timestamp="2026-09-04T00:00:00Z")
        assert artifact is not None and artifact.status == "PENDING"
        # result file must land inside the encrypted volume, not the source tree
        output_path = Path(artifact.output)
        assert str(output_path).startswith(str(MOUNT_ROOT))
        assert output_path.exists() and output_path.stat().st_size > 0
        shutil.rmtree(workspace_root / "projects" / project_id, ignore_errors=True)
