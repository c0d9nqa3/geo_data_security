from pathlib import Path
import sys

import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.robust_geotiff_watermark import (
    embed_geotiff_watermark_robust,
    extract_geotiff_watermark_robust,
)

REAL_B1 = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")
EXPECTED = 0xA5A5F00D


def _variants(watermarked: Path, tmp_path: Path):
    with rasterio.open(watermarked) as ds:
        height, width = ds.height, ds.width
        crop_h, crop_w = height // 2, width // 2
        window = Window((width - crop_w) // 2, (height - crop_h) // 2, crop_w, crop_h)
        crop = tmp_path / "crop.tif"
        profile = ds.profile.copy()
        profile.update(width=crop_w, height=crop_h, transform=ds.window_transform(window))
        with rasterio.open(crop, "w", **profile) as out:
            out.update_tags(**ds.tags())
            out.write(ds.read(window=window))

        resize = tmp_path / "resize.tif"
        profile = ds.profile.copy()
        profile.update(width=width // 2, height=height // 2, transform=ds.transform * Affine.scale(2, 2))
        data = ds.read(out_shape=(ds.count, height // 2, width // 2), resampling=Resampling.bilinear)
        with rasterio.open(resize, "w", **profile) as out:
            out.update_tags(**ds.tags())
            out.write(data)
    return crop, resize


def test_robust_carrier_real_b1_survives_crop_and_resize(tmp_path):
    watermarked = tmp_path / "watermarked.tif"
    embed_geotiff_watermark_robust(REAL_B1, watermarked, EXPECTED)
    crop, resize = _variants(watermarked, tmp_path)
    assert extract_geotiff_watermark_robust(watermarked) == EXPECTED
    assert extract_geotiff_watermark_robust(crop) == EXPECTED
    assert extract_geotiff_watermark_robust(resize) == EXPECTED
