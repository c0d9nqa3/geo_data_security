from pathlib import Path
import hashlib
import json
import time
import traceback

import rasterio

from geo_security.geotiff_watermark import embed_geotiff_watermark, extract_geotiff_watermark

ROOT = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00")
OUT = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/landsat_full_final")
OUT.mkdir(parents=True, exist_ok=True)
rows = []
keys = ["width", "height", "count", "crs", "transform", "bounds"]
expected = 0xA5A5F00D

for source in sorted(ROOT.glob("*.TIF")):
    destination = OUT / f"{source.stem}_watermarked.tif"
    started = time.perf_counter()
    row = {"input": str(source), "output": str(destination), "status": "FAILED"}
    try:
        with rasterio.open(source) as dataset:
            before = {
                "width": dataset.width,
                "height": dataset.height,
                "count": dataset.count,
                "dtype": dataset.dtypes,
                "crs": str(dataset.crs),
                "transform": tuple(dataset.transform),
                "bounds": tuple(dataset.bounds),
                "tags": dataset.tags(),
            }
        quality = embed_geotiff_watermark(source, destination, expected)
        extracted = extract_geotiff_watermark(destination)
        with rasterio.open(destination) as dataset:
            after = {
                "width": dataset.width,
                "height": dataset.height,
                "count": dataset.count,
                "dtype": dataset.dtypes,
                "crs": str(dataset.crs),
                "transform": tuple(dataset.transform),
                "bounds": tuple(dataset.bounds),
                "tags": dataset.tags(),
            }
        spatial_ok = all(before[key] == after[key] for key in keys)
        spatial_ok = spatial_ok and before["tags"].get("AREA_OR_POINT") == after["tags"].get("AREA_OR_POINT")
        dtype_preserved = before["dtype"] == after["dtype"]
        row.update({
            "seconds": round(time.perf_counter() - started, 3),
            "psnr_db": quality,
            "psnr_over_40db": quality > 40.0,
            "extracted_watermark": hex(extracted),
            "watermark_ok": extracted == expected,
            "spatial_metadata_ok": spatial_ok,
            "dtype_preserved": dtype_preserved,
            "input_dtype": before["dtype"],
            "output_dtype": after["dtype"],
            "input_area_or_point": before["tags"].get("AREA_OR_POINT"),
            "output_area_or_point": after["tags"].get("AREA_OR_POINT"),
            "input_bytes": source.stat().st_size,
            "output_bytes": destination.stat().st_size,
            "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "status": "PASS" if extracted == expected and spatial_ok and quality > 40.0 else "FAIL",
        })
    except Exception as exc:
        row.update({"seconds": round(time.perf_counter() - started, 3), "error": repr(exc), "traceback": traceback.format_exc()})
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

report = OUT / "report.json"
report.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
summary = {
    "report": str(report),
    "count": len(rows),
    "passed": sum(row["status"] == "PASS" for row in rows),
    "min_psnr_db": min(row["psnr_db"] for row in rows if "psnr_db" in row),
    "max_seconds": max(row["seconds"] for row in rows),
    "total_seconds": round(sum(row["seconds"] for row in rows), 3),
}
print(json.dumps(summary, ensure_ascii=False))
