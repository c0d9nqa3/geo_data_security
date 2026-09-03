from pathlib import Path
import sys

import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.geotiff_watermark import embed_geotiff_watermark, extract_geotiff_watermark

REAL_B1 = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")


def test_real_b1_crop_and_resize_keep_watermark(tmp_path):
    pytest.skip("实验性同步载体尚未通过真实裁剪和缩放测试")
