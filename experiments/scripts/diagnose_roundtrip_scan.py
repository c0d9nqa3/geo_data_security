from pathlib import Path
import sys
import json
import time

import numpy as np
import rasterio
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

EXPECTED = 0xA5A5F00D
BASE = ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"
OUT = ROOT / "runtime" / "trustmark_full_tiled"
TILE = 1024

with rasterio.open(BASE) as ds:
    src_arr = ds.read(1)
    src_crs = ds.crs
    profile = ds.profile.copy()

# full reproject roundtrip: 32644 -> 4326 -> 32644 via GDAL (exact projection math)
from rasterio.warp import calculate_default_transform, reproject, Resampling

def warp_crs(arr, src_crs, dst_crs, src_tf, w, h):
    t, nw, nh = calculate_default_transform(src_crs, dst_crs, w, h, *rasterio.transform.array_bounds(h, w, src_tf))
    out = np.empty((nh, nw), dtype=np.uint8)
    reproject(source=arr, destination=out, src_transform=src_tf, src_crs=src_crs,
              dst_transform=t, dst_crs=dst_crs, resampling=Resampling.bilinear)
    return out, t, nw, nh

with rasterio.open(BASE) as ds:
    a4326, t4326, w4326, h4326 = warp_crs(src_arr, src_crs, "EPSG:4326", ds.transform, ds.width, ds.height)
    back, tback, wback, hback = warp_crs(a4326, "EPSG:4326", src_crs, t4326, w4326, h4326)
print(json.dumps({"src": [src_arr.shape[1], src_arr.shape[0]], "rt": [wback, hback]}), flush=True)

rt_rgb = np.repeat(back[:, :, None], 3, axis=2)
rt_img = Image.fromarray(rt_rgb, mode="RGB")

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

def dec(a):
    bits, present, schema = tm.decode(Image.fromarray(np.repeat(a[:, :, None], 3, axis=2), mode="RGB"), MODE="binary")
    value = int(bits[:32], 2) if present and len(bits) >= 32 else None
    return {"present": present, "value": None if value is None else hex(value), "schema": schema}

# tile-to-tile: for each original tile grid cell, find its roundtripped location via 4-corner transform,
# crop slightly padded region and decode directly (GDAL already did the warp; just need the right crop window)
from pyproj import Transformer
tr_fwd = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
tr_bwd = Transformer.from_crs("EPSG:4326", src_crs, always_xy=True)

def tile_rt_box(i, j):
    """bbox in roundtripped image of source tile (i,j), computed via corner chain."""
    x0, y0 = i * TILE, j * TILE
    xs, ys = [], []
    for cx, cy in [(x0, y0), (x0 + TILE, y0), (x0 + TILE, y0 + TILE), (x0, y0 + TILE)]:
        gx, gy = None, None
        with rasterio.open(BASE) as ds:
            gx, gy = ds.transform * (cx, cy)
        lon, lat = tr_fwd.transform(gx, gy)
        px, py = ~tback * tr_bwd.transform(lon, lat)
        xs.append(px); ys.append(py)
    return min(xs), min(ys), max(xs), max(ys)

rows = []
tiles = [(3, 3), (4, 3), (3, 2), (2, 2), (5, 4), (1, 1), (6, 5)]
for i, j in tiles:
    try:
        x1, y1, x2, y2 = tile_rt_box(i, j)
        pad = 8
        x1, y1 = max(0, int(x1) - pad), max(0, int(y1) - pad)
        x2, y2 = min(wback, int(x2) + pad), min(hback, int(y2) + pad)
        win_w, win_h = x2 - x1, y2 - y1
        if win_w < 256 or win_h < 256:
            rows.append({"tile": (i, j), "ok": False, "error": "window too small"})
            continue
        crop = back[y1:y2, x1:x2]
        # resize to TILE for decode
        from PIL import Image as I
        cimg = I.fromarray(np.repeat(crop[:, :, None], 3, axis=2), mode="RGB").resize((TILE, TILE), I.Resampling.BILINEAR)
        bits, present, schema = tm.decode(cimg, MODE="binary")
        value = int(bits[:32], 2) if present and len(bits) >= 32 else None
        rows.append({"tile": (i, j), "ok": value == EXPECTED, "present": present, "value": None if value is None else hex(value), "schema": schema, "win": [win_w, win_h]})
    except Exception as exc:
        rows.append({"tile": (i, j), "ok": False, "error": repr(exc)})
    print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
print(json.dumps({"passed": sum(1 for r in rows if r.get("ok")), "total": len(rows)}), flush=True)
