"""RED: TrustMark runner extract 应支持重投影攻击图（4326 逆投影回原网格再解码）。

本测试用 runner embed 的真实水印文件 -> rasterio 重投影到 EPSG:4326 -> 再经引擎
extract。runner 需要能识别目标 CRS 与原 CRS 不一致并先做 GDAL 逆投影，否则失败。
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

TRUSTMARK_PYTHON = ROOT / "runtime" / "trustmark_venv" / "Scripts" / "python.exe"
TRUSTMARK_RUNNER = ROOT / "server2" / "pipeline" / "geo_security" / "trustmark_geotiff_runner.py"
HAS_TRUSTMARK_ENV = TRUSTMARK_PYTHON.exists() and TRUSTMARK_RUNNER.exists()

pytestmark = pytest.mark.skipif(not HAS_TRUSTMARK_ENV, reason="TrustMark isolated venv not present")


def _make_geotiff(path: Path, size: int = 1024) -> None:
    rng = np.random.default_rng(21)
    values = rng.integers(0, 256, (size, size), dtype=np.uint8)
    profile = {
        "driver": "GTiff", "height": size, "width": size, "count": 1, "dtype": "uint8",
        "crs": "EPSG:32644", "transform": rasterio.transform.from_origin(500000, 4000000, 30, 30),
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(values, 1)
        ds.update_tags(AREA_OR_POINT="Area")


def _reproject_to_4326(source: Path, destination: Path) -> None:
    with rasterio.open(source) as ds:
        transform, width, height = calculate_default_transform(
            ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds
        )
        profile = ds.profile.copy()
        profile.update(crs="EPSG:4326", transform=transform, width=width, height=height)
        tags = ds.tags()
        destination_array = np.empty((height, width), dtype=np.uint8)
        reproject(
            source=rasterio.band(ds, 1),
            destination=destination_array,
            src_transform=ds.transform,
            src_crs=ds.crs,
            dst_transform=transform,
            dst_crs="EPSG:4326",
            resampling=Resampling.bilinear,
        )
    with rasterio.open(destination, "w", **profile) as ds:
        ds.update_tags(**tags)  # GDAL gdalwarp keeps file tags by default
        ds.write(destination_array, 1)


def test_engine_extract_detects_watermark_after_reprojection(tmp_path):
    from geo_security.trustmark_engine import TrustMarkGeoTIFFEngine

    source = tmp_path / "src.tif"
    marked = tmp_path / "marked.tif"
    reprojected = tmp_path / "reprojected.tif"
    _make_geotiff(source, size=1024)
    engine = TrustMarkGeoTIFFEngine(python=str(TRUSTMARK_PYTHON), runner=str(TRUSTMARK_RUNNER), timeout=1800)
    engine.embed(source, marked, 0x1357BDFF)
    _reproject_to_4326(marked, reprojected)
    # confirm the attack image actually carries a different CRS
    with rasterio.open(reprojected) as ds:
        assert str(ds.crs) != "EPSG:32644"
    result = engine.extract(reprojected, 0x1357BDFF)
    assert result.get("detected") is True, result
