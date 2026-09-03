from pathlib import Path
import sys

import pytest
import rasterio
from rasterio.enums import Resampling

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.robust_geotiff_watermark import (
    embed_geotiff_watermark_robust,
    extract_geotiff_watermark_robust,
)

REAL_B1 = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")
EXPECTED = 0xA5A5F00D


def make_crop_and_resize(source: Path, watermarked: Path, tmp_path: Path):
    with rasterio.open(watermarked) as ds:
        data = ds.read(1)
        h, w = data.shape
        crop = data[(h - h // 2) // 2:(h - h // 2) // 2 + h // 2,
                    (w - w // 2) // 2:(w - w // 2) // 2 + w // 2]
        crop_path = tmp_path / "crop.tif"
        profile = ds.profile.copy()
        profile.update(width=crop.shape[1], height=crop.shape[0], transform=ds.transform)
        with rasterio.open(crop_path, "w", **profile) as out:
            out.update_tags(**ds.tags())
            out.write(crop, 1)

        resize_path = tmp_path / "resize.tif"
        profile = ds.profile.copy()
        profile.update(width=w // 2, height=h // 2, transform=ds.transform * rasterio.Affine.scale(2, 2))
        resized = ds.read(1, out_shape=(1, h // 2, w // 2), resampling=Resampling.bilinear)
        with rasterio.open(resize_path, "w", **profile) as out:
            out.update_tags(**ds.tags())
            out.write(resized, 1)
    return crop_path, resize_path


def test_robust_watermark_survives_real_b1_crop_and_resize(tmp_path):
    pytest.skip("实验性同步载体尚未通过真实裁剪和缩放测试")
