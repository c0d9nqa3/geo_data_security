from pathlib import Path
import sys
import json
import time

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

EXPECTED = 0xA5A5F00D
BASE = ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"
TILE = 1024

with rasterio.open(BASE) as ds:
    src_crs = ds.crs
    src_arr0 = ds.read(1)

from rasterio.warp import calculate_default_transform, reproject, Resampling

# warp 32644 -> 4326 (single direction)
with rasterio.open(BASE) as ds:
    t4326, w4326, h4326 = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
    a4326 = np.empty((h4326, w4326), dtype=np.uint8)
    reproject(source=ds.read(1), destination=a4326, src_transform=ds.transform, src_crs=ds.crs,
              dst_transform=t4326, dst_crs="EPSG:4326", resampling=Resampling.bilinear)

tr_bwd = Transformer.from_crs("EPSG:4326", src_crs, always_xy=True)
tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

tr_fwd = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)


def quad_bbox_4326(i, j):
    with rasterio.open(BASE) as ds:
        tf = ds.transform
    x0, y0 = i * TILE, j * TILE
    xs, ys = [], []
    for cx, cy in [(x0, y0), (x0 + TILE, y0), (x0 + TILE, y0 + TILE), (x0, y0 + TILE)]:
        gx, gy = tf * (cx, cy)
        lon, lat = tr_fwd.transform(gx, gy)
        px, py = ~t4326 * (lon, lat)
        xs.append(px); ys.append(py)
    return min(xs), min(ys), max(xs), max(ys)


rows = []
tiles = [(3, 3), (4, 3), (3, 2), (2, 2), (5, 4), (1, 1), (6, 5), (3, 4), (4, 4), (5, 3)]
for i, j in tiles:
    try:
        x1, y1, x2, y2 = quad_bbox_4326(i, j)
        pad = 6
        x1, y1 = max(0, int(x1) - pad), max(0, int(y1) - pad)
        x2, y2 = min(w4326, int(x2) + pad), min(h4326, int(y2) + pad)
        win_w, win_h = x2 - x1, y2 - y1
        if win_w < 200 or win_h < 200:
            rows.append({"tile": (i, j), "ok": False, "error": "window small", "win": [win_w, win_h]})
            continue
        crop = a4326[y1:y2, x1:x2]
        cimg = Image.fromarray(np.repeat(crop[:, :, None], 3, axis=2), mode="RGB").resize((TILE, TILE), Image.Resampling.BILINEAR)
        bits, present, schema = tm.decode(cimg, MODE="binary")
        value = int(bits[:32], 2) if present and len(bits) >= 32 else None
        rows.append({"tile": (i, j), "ok": value == EXPECTED, "present": present, "value": None if value is None else hex(value), "schema": schema, "win": [win_w, win_h]})
    except Exception as exc:
        rows.append({"tile": (i, j), "ok": False, "error": repr(exc)})
    print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
print(json.dumps({"passed": sum(1 for r in rows if r.get("ok")), "total": len(rows)}), flush=True)
