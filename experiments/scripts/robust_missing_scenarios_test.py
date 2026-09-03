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


def make_variants(watermarked: Path, tmp_path: Path):
    with rasterio.open(watermarked) as ds:
        h, w = ds.height, ds.width
        resize25 = tmp_path / "resize25.tif"
        profile = ds.profile.copy()
        profile.update(width=max(512, w // 4), height=max(512, h // 4), transform=ds.transform * Affine.scale(4, 4))
        data = ds.read(out_shape=(ds.count, max(512, h // 4), max(512, w // 4)), resampling=Resampling.bilinear)
        with rasterio.open(resize25, "w", **profile) as out:
            out.update_tags(**ds.tags())
            out.write(data)

        reprojected = tmp_path / "reprojected.tif"
        from rasterio.warp import calculate_default_transform, reproject
        transform, width, height = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
        profile = ds.profile.copy()
        profile.update(crs="EPSG:4326", transform=transform, width=width, height=height)
        data = __import__("numpy").zeros((height, width), dtype="uint8")
        reproject(ds.read(1), data, src_transform=ds.transform, src_crs=ds.crs, dst_transform=transform, dst_crs="EPSG:4326", resampling=Resampling.bilinear)
        with rasterio.open(reprojected, "w", **profile) as out:
            out.update_tags(**ds.tags())
            out.write(data, 1)
    return resize25, reprojected


def test_robust_carrier_handles_25_percent_resize_and_reprojection(tmp_path):
    watermarked = tmp_path / "watermarked.tif"
    embed_geotiff_watermark_robust(REAL_B1, watermarked, EXPECTED)
    resize25, reprojected = make_variants(watermarked, tmp_path)
    assert extract_geotiff_watermark_robust(resize25) == EXPECTED
    assert extract_geotiff_watermark_robust(reprojected) == EXPECTED
