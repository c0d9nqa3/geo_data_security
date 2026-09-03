from pathlib import Path
import sys
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))
from geo_security.geotiff_watermark import embed_geotiff_watermark, extract_geotiff_watermark, psnr


REAL_B1 = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")


def test_real_uint8_roundtrip_keeps_uint8_and_meets_psnr(tmp_path):
    destination = tmp_path / "b1_watermarked.tif"
    embed_geotiff_watermark(REAL_B1, destination, 0xA5A5F00D)
    with rasterio.open(REAL_B1) as source, rasterio.open(destination) as output:
        assert output.dtypes == source.dtypes == ("uint8",)
        assert output.crs == source.crs
        assert output.transform == source.transform
        assert output.width == source.width and output.height == source.height
        assert psnr(source.read(1), output.read(1)) > 40.0
    assert extract_geotiff_watermark(destination) == 0xA5A5F00D
