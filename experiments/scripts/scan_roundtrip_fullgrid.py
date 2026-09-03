from pathlib import Path
import sys
import json

import numpy as np
import rasterio
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

EXPECTED = 0xA5A5F00D
BASE = ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"
TILE = 1024

with rasterio.open(BASE) as ds:
    src_crs = ds.crs
    src_tf = ds.transform
    src_arr = ds.read(1)
    sw, sh = ds.width, ds.height

from rasterio.warp import calculate_default_transform, reproject, Resampling

def warp_roundtrip():
    with rasterio.open(BASE) as ds:
        t1, w1, h1 = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
        a1 = np.empty((h1, w1), dtype=np.uint8)
        reproject(source=ds.read(1), destination=a1, src_transform=ds.transform, src_crs=ds.crs,
                  dst_transform=t1, dst_crs="EPSG:4326", resampling=Resampling.bilinear)
        # back to original CRS but with new grid
        t2, w2, h2 = calculate_default_transform("EPSG:4326", ds.crs, w1, h1, *rasterio.transform.array_bounds(h1, w1, t1))
        a2 = np.empty((h2, w2), dtype=np.uint8)
        reproject(source=a1, destination=a2, src_transform=t1, src_crs="EPSG:4326",
                  dst_transform=t2, dst_crs=ds.crs, resampling=Resampling.bilinear)
    return a2, t2

back, tback = warp_roundtrip()
print(json.dumps({"roundtrip_size": [back.shape[1], back.shape[0]], "src_size": [sw, sh]}), flush=True)

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

def decode_tile(i, j):
    """bbox from 4-corner transform chain (proven method), decode center crop."""
    x0, y0 = i * TILE, j * TILE
    xs, ys = [], []
    for cx, cy in [(x0, y0), (x0 + TILE, y0), (x0 + TILE, y0 + TILE), (x0, y0 + TILE)]:
        gx, gy = src_tf * (cx, cy)
        px, py = ~tback * (gx, gy)
        xs.append(px); ys.append(py)
    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
    pad = 8
    x1, y1 = max(0, int(x1) - pad), max(0, int(y1) - pad)
    x2, y2 = min(back.shape[1], int(x2) + pad), min(back.shape[0], int(y2) + pad)
    crop = back[y1:y2, x1:x2]
    if crop.shape[0] < 256 or crop.shape[1] < 256:
        return {"present": False, "value": None, "schema": -1, "bbox": (x1, y1, x2, y2)}
    cimg = Image.fromarray(np.repeat(crop[:, :, None], 3, axis=2), mode="RGB").resize((TILE, TILE), Image.Resampling.BILINEAR)
    bits, present, schema = tm.decode(cimg, MODE="binary")
    value = int(bits[:32], 2) if present and len(bits) >= 32 else None
    return {"present": present, "value": None if value is None else hex(value), "schema": schema, "bbox": (x1, y1, x2, y2)}

results = []
ok_tiles = []
for j in range(0, 7):
    for i in range(0, 7):
        if i * TILE >= sw or j * TILE >= sh:
            continue
        r = decode_tile(i, j)
        ok = r["value"] == hex(EXPECTED) or (r["value"] is not None and int(r["value"], 16) == EXPECTED)
        results.append({"tile": (i, j), "ok": ok, **r})
        if ok:
            ok_tiles.append((i, j))
n = len(results)
passed = sum(1 for r in results if r["ok"])
print(json.dumps({"passed": passed, "total": n, "rate": round(passed / n, 3), "ok_tiles": ok_tiles}), flush=True)
(Path(ROOT) / "runtime" / "trustmark_full_tiled" / "report_roundtrip_scan.json").write_text(json.dumps({"results": results, "passed": passed, "total": n}, ensure_ascii=False, indent=2), encoding="utf-8")
