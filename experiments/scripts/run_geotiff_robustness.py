from __future__ import annotations

from pathlib import Path
import json
import time
import traceback

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window
from rasterio.transform import Affine

from geo_security.geotiff_watermark import extract_geotiff_watermark

DATA = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00")
BASE = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/landsat_full_final")
OUT = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/landsat_robustness")
EXPECTED = 0xA5A5F00D
OUT.mkdir(parents=True, exist_ok=True)


def source_meta(path: Path) -> dict:
    with rasterio.open(path) as ds:
        return {
            "width": ds.width, "height": ds.height, "count": ds.count,
            "dtype": ds.dtypes, "crs": str(ds.crs),
            "transform": tuple(ds.transform), "bounds": tuple(ds.bounds),
            "tags": ds.tags(),
        }


def write_compressed(src: Path, dst: Path) -> None:
    with rasterio.open(src) as ds:
        profile = ds.profile.copy()
        profile.update(compress="deflate", tiled=True, blockxsize=256, blockysize=256)
        with rasterio.open(dst, "w", **profile) as out:
            out.update_tags(**ds.tags())
            out.write(ds.read())


def write_png(src: Path, dst: Path) -> None:
    with rasterio.open(src) as ds:
        data = ds.read(1)
        profile = ds.profile.copy()
        profile.update(driver="PNG", count=1, dtype="uint8", compress=None)
        with rasterio.open(dst, "w", **profile) as out:
            out.update_tags(**ds.tags())
            out.write(data, 1)


def write_crop(src: Path, dst: Path) -> None:
    with rasterio.open(src) as ds:
        width, height = ds.width // 2, ds.height // 2
        col, row = (ds.width - width) // 2, (ds.height - height) // 2
        window = Window(col, row, width, height)
        profile = ds.profile.copy()
        profile.update(width=width, height=height, transform=ds.window_transform(window))
        with rasterio.open(dst, "w", **profile) as out:
            out.update_tags(**ds.tags())
            out.write(ds.read(window=window))


def write_resize(src: Path, dst: Path) -> None:
    with rasterio.open(src) as ds:
        width, height = ds.width // 2, ds.height // 2
        profile = ds.profile.copy()
        profile.update(width=width, height=height, transform=ds.transform * Affine.scale(2, 2))
        data = ds.read(out_shape=(ds.count, height, width), resampling=Resampling.bilinear)
        with rasterio.open(dst, "w", **profile) as out:
            out.update_tags(**ds.tags())
            out.write(data)


writers = {
    "geotiff_deflate": write_compressed,
    "format_png": write_png,
    "crop_center_50": write_crop,
    "resize_50_bilinear": write_resize,
}
rows = []
for base in sorted(BASE.glob("*_watermarked.tif")):
    band = base.stem.replace("_watermarked", "")
    for name, writer in writers.items():
        dst = OUT / f"{band}_{name}{'.png' if name == 'format_png' else '.tif'}"
        started = time.perf_counter()
        row = {"band": band, "scenario": name, "path": str(dst), "status": "FAIL"}
        try:
            writer(base, dst)
            output_info = source_meta(dst)
            extracted = extract_geotiff_watermark(dst)
            with rasterio.open(dst) as out_ds:
                transformed_data = out_ds.read(1)
            row.update({
                "seconds": round(time.perf_counter() - started, 3),
                "watermark": hex(extracted),
                "watermark_ok": extracted == EXPECTED,
                "dtype": output_info["dtype"],
                "width": output_info["width"], "height": output_info["height"],
                "crs": output_info["crs"],
                "transform": output_info["transform"],
                "spatial_reference_present": output_info["crs"] != "None",
                "status": "PASS" if extracted == EXPECTED else "FAIL",
            })
        except Exception as exc:
            row.update({"seconds": round(time.perf_counter() - started, 3), "error": repr(exc), "traceback": traceback.format_exc()})
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

summary = {}
for name in writers:
    subset = [row for row in rows if row["scenario"] == name]
    summary[name] = {"count": len(subset), "passed": sum(row["status"] == "PASS" for row in subset), "rate": sum(row["status"] == "PASS" for row in subset) / len(subset) if subset else 0}
report = {"expected_watermark": hex(EXPECTED), "results": rows, "summary": summary}
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"report": str(OUT / 'report.json'), "summary": summary}, ensure_ascii=False))
