from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.feature_robust_watermark import (
    embed_feature_watermark,
    extract_feature_watermark,
)

REAL_B1 = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")


def test_feature_watermark_api_is_still_explicit(tmp_path):
    pytest.importorskip("cv2")
    output = tmp_path / "watermarked.tif"
    embed_feature_watermark(REAL_B1, output, 0xA5A5F00D)
    assert extract_feature_watermark(output) == 0xA5A5F00D
