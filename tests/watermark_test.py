import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "server2" / "pipeline"
sys.path.insert(0, str(PACKAGE))

from geo_security.crypto import decrypt_text
from geo_security.geotiff_watermark import embed_geotiff_watermark, extract_geotiff_watermark, psnr
from geo_security.geojson_watermark import embed_geojson_watermark, extract_geojson_watermark


def test_geojson_adds_encrypted_watermark_without_changing_geometry(tmp_path):
    source = tmp_path / "source.geojson"
    source.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"name": "A"}, "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
            {"type": "Feature", "properties": {"name": "B"}, "geometry": {"type": "LineString", "coordinates": [[1.0, 2.0], [3.0, 4.0]]}},
        ],
    }), encoding="utf-8")
    destination = tmp_path / "watermarked.geojson"

    embed_geojson_watermark(source, destination, "user-1|project-1", b"key")
    output = json.loads(destination.read_text(encoding="utf-8"))
    original = json.loads(source.read_text(encoding="utf-8"))

    assert [f["geometry"] for f in output["features"]] == [f["geometry"] for f in original["features"]]
    assert all("_wm" in f["properties"] for f in output["features"])
    assert all(decrypt_text(f["properties"]["_wm"], b"key") == "user-1|project-1" for f in output["features"])
    assert extract_geojson_watermark(destination, b"key") == ["user-1|project-1", "user-1|project-1"]


def test_geotiff_preserves_spatial_metadata_and_round_trips_32_bit_watermark(tmp_path):
    source = tmp_path / "source.tif"
    destination = tmp_path / "watermarked.tif"
    values = np.arange(64 * 64, dtype=np.float32).reshape(64, 64)
    profile = {
        "driver": "GTiff", "height": 64, "width": 64, "count": 1,
        "dtype": "float32", "crs": "EPSG:4326", "transform": from_origin(117, 41, 0.01, 0.01),
    }
    with rasterio.open(source, "w", **profile) as dataset:
        dataset.write(values, 1)

    embed_geotiff_watermark(source, destination, 0xA5A5F00D)
    with rasterio.open(source) as before, rasterio.open(destination) as after:
        assert after.crs == before.crs
        assert after.transform == before.transform
        assert (after.width, after.height, after.count) == (before.width, before.height, before.count)
        quality = psnr(before.read(1), after.read(1))
        assert quality > 40.0
    assert extract_geotiff_watermark(destination) == 0xA5A5F00D
