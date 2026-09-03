from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window
from rasterio.transform import Affine

from geo_security.robust_geotiff_watermark import (
    embed_geotiff_watermark_robust,
    extract_geotiff_watermark_robust,
)

DATA = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00")
OUT = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/robust_b1_b7")
EXPECTED = 0xA5A5F00D
OUT.mkdir(parents=True, exist_ok=True)


def meta(path: Path) -> dict:
    with rasterio.open(path) as ds:
        return {
            "width": ds.width, "height": ds.height, "count": ds.count,
            "dtype": ds.dtypes, "crs": str(ds.crs),
            "transform": tuple(ds.transform), "bounds": tuple(ds.bounds),
            "tags": ds.tags(),
        }


def make_variants(watermarked: Path, band_dir: Path) -> tuple[Path, Path]:
    with rasterio.open(watermarked) as ds:
        h, w = ds.height, ds.width
        crop_h, crop_w = h // 2, w // 2
        window = Window((w - crop_w) // 2, (h - crop_h) // 2, crop_w, crop_h)
        crop_path = band_dir / "crop50.tif"
        crop_profile = ds.profile.copy()
        crop_profile.update(width=crop_w, height=crop_h, transform=ds.window_transform(window))
        with rasterio.open(crop_path, "w", **crop_profile) as out:
            out.update_tags(**ds.tags())
            out.write(ds.read(window=window))

        resize_path = band_dir / "resize50.tif"
        resize_profile = ds.profile.copy()
        resize_profile.update(width=w // 2, height=h // 2, transform=ds.transform * Affine.scale(2, 2))
        resized = ds.read(out_shape=(ds.count, h // 2, w // 2), resampling=Resampling.bilinear)
        with rasterio.open(resize_path, "w", **resize_profile) as out:
            out.update_tags(**ds.tags())
            out.write(resized)
    return crop_path, resize_path


rows = []
for source in sorted(DATA.glob("*.TIF")):
    band_dir = OUT / source.stem
    band_dir.mkdir(parents=True, exist_ok=True)
    watermarked = band_dir / "watermarked.tif"
    started = time.perf_counter()
    row = {"band": source.stem, "status": "FAIL"}
    try:
        before = meta(source)
        psnr = embed_geotiff_watermark_robust(source, watermarked, EXPECTED)
        after = meta(watermarked)
        full_value = extract_geotiff_watermark_robust(watermarked)
        crop, resize = make_variants(watermarked, band_dir)
        crop_value = extract_geotiff_watermark_robust(crop)
        resize_value = extract_geotiff_watermark_robust(resize)
        spatial_keys = ["width", "height", "count", "crs", "transform", "bounds"]
        spatial_ok = all(before[key] == after[key] for key in spatial_keys)
        dtype_ok = before["dtype"] == after["dtype"] == ("uint8",)
        row.update({
            "seconds": round(time.perf_counter() - started, 3),
            "psnr_db": psnr,
            "psnr_over_40db": psnr > 40.0,
            "dtype_ok": dtype_ok,
            "spatial_metadata_ok": spatial_ok,
            "full_watermark": hex(full_value),
            "crop50_watermark": hex(crop_value),
            "resize50_watermark": hex(resize_value),
            "full_ok": full_value == EXPECTED,
            "crop50_ok": crop_value == EXPECTED,
            "resize50_ok": resize_value == EXPECTED,
            "status": "PASS" if dtype_ok and spatial_ok and psnr > 40.0 and full_value == EXPECTED and crop_value == EXPECTED and resize_value == EXPECTED else "FAIL",
        })
    except Exception as exc:
        row.update({"seconds": round(time.perf_counter() - started, 3), "error": repr(exc)})
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

summary = {
    "bands": len(rows),
    "passed": sum(row["status"] == "PASS" for row in rows),
    "embedding_rate": sum(row.get("full_ok", False) for row in rows) / len(rows),
    "crop50_rate": sum(row.get("crop50_ok", False) for row in rows) / len(rows),
    "resize50_rate": sum(row.get("resize50_ok", False) for row in rows) / len(rows),
    "psnr_min_db": min(row["psnr_db"] for row in rows if "psnr_db" in row),
    "max_seconds": max(row["seconds"] for row in rows),
    "total_seconds": round(sum(row["seconds"] for row in rows), 3),
}
report = {"expected_watermark": hex(EXPECTED), "results": rows, "summary": summary}
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"report": str(OUT / "report.json"), "summary": summary}, ensure_ascii=False))
