"""纹理水印引擎矩阵: ProcessingService(注入 TrustMark) 嵌入真实风格纹理,
JPEG/缩放/噪声攻击后经引擎 extract_image 识别。无 TrustMark venv 时跳过。
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.processing import ProcessingService  # noqa: E402
from geo_security.trustmark_engine import TrustMarkGeoTIFFEngine  # noqa: E402

WM = 0xA5A5F00D

try:
    engine = TrustMarkGeoTIFFEngine()
    HAVE_TM = True
except Exception:  # noqa: BLE001
    HAVE_TM = False

rng = np.random.default_rng(7)


def _photo_texture(kind: str) -> np.ndarray:
    y, x = np.mgrid[0:512, 0:512]
    base = np.zeros((512, 512, 3), dtype=np.uint8)
    if kind == "gradient":
        base[:, :, 0] = (x * 0.3 + y * 0.2).astype(np.uint8)
        base[:, :, 1] = (255 - y * 0.3).astype(np.uint8)
        base[:, :, 2] = (x * 0.2 + 40).astype(np.uint8)
    elif kind == "urban":
        base[:, :, 0] = ((x // 32) * 40 % 255).astype(np.uint8)
        base[:, :, 1] = ((y // 32) * 30 % 255).astype(np.uint8)
        base[:, :, 2] = (((x + y) // 64) * 60 % 255).astype(np.uint8)
    else:
        base[:, :, 0] = (128 + 60 * np.sin(x / 40) * np.cos(y / 30)).astype(np.uint8)
        base[:, :, 1] = (100 + 40 * np.sin((x + y) / 25)).astype(np.uint8)
        base[:, :, 2] = (90 + 50 * np.cos(y / 20)).astype(np.uint8)
    return np.clip(base.astype(np.float64) + rng.normal(0, 6, base.shape), 0, 255).astype(np.uint8)


@pytest.mark.skipif(not HAVE_TM, reason="TrustMark venv not present")
class TestTrustMarkTextureEngine:
    def _embed_textures(self, tmp_path, kinds=("gradient", "urban", "natural")):
        src_dir = tmp_path / "textures"
        src_dir.mkdir()
        for kind in kinds:
            Image.fromarray(_photo_texture(kind)).save(src_dir / f"{kind}.png")
        ws = tmp_path / "ws"
        service = ProcessingService(workspace=ws, key=b"k", trustmark_engine=engine)
        artifact = service.process("p1", "TEXTURES", src_dir, watermark=WM)
        return artifact

    def test_texture_embed_roundtrip_all_kinds(self, tmp_path):
        artifact = self._embed_textures(tmp_path)
        assert artifact.files_processed == 3
        result_dir = Path(artifact.output)
        for kind in ("gradient", "urban", "natural"):
            res = engine.extract_image(result_dir / f"{kind}.png", WM)
            assert res["detected"], f"{kind}: {res}"

    def test_texture_jpeg_q85_survives(self, tmp_path):
        artifact = self._embed_textures(tmp_path)
        result_dir = Path(artifact.output)
        passed = 0
        for kind in ("gradient", "urban", "natural"):
            jpg = result_dir / f"{kind}.jpg"
            Image.open(result_dir / f"{kind}.png").save(jpg, "JPEG", quality=85)
            res = engine.extract_image(jpg, WM)
            if res["detected"]:
                passed += 1
        assert passed == 3, "JPEG q85 should survive on all texture kinds"

    def test_texture_resize_50_survives(self, tmp_path):
        artifact = self._embed_textures(tmp_path)
        result_dir = Path(artifact.output)
        passed = 0
        for kind in ("gradient", "urban", "natural"):
            half = result_dir / f"{kind}_half.png"
            im = Image.open(result_dir / f"{kind}.png")
            im.resize((im.width // 2, im.height // 2), Image.Resampling.BILINEAR).save(half)
            res = engine.extract_image(half, WM)
            if res["detected"]:
                passed += 1
        assert passed == 3, "resize 50% should survive on all texture kinds"
