from pathlib import Path
import sys
import json

import numpy as np
import rasterio
from PIL import Image
import cv2
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

EXPECTED = 0xA5A5F00D
BASE = ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"
OUT = ROOT / "runtime" / "trustmark_full_tiled"

with rasterio.open(BASE) as ds:
    src_arr = ds.read(1)
    src_crs = ds.crs
    src_tf = ds.transform
    sh, sw = src_arr.shape

# build reprojected 4326 image (as the attacked artifact)
from rasterio.warp import calculate_default_transform, reproject, Resampling
with rasterio.open(BASE) as ds:
    dst_tf, nw2, nh2 = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
    wrp = np.empty((nh2, nw2), dtype=np.uint8)
    reproject(source=src_arr, destination=wrp, src_transform=ds.transform, src_crs=ds.crs,
              dst_transform=dst_tf, dst_crs="EPSG:4326", resampling=Resampling.bilinear)
print(json.dumps({"reproj": [nw2, nh2], "src": [sw, sh], "src_tf": [src_tf.a, src_tf.d, src_tf.b, src_tf.e], "dst_tf": [dst_tf.a, dst_tf.d, dst_tf.b, dst_tf.e]}), flush=True)

tr = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
TILE = 1024


def warp_tile_back(i, j):
    """Map source tile (i,j) corners to dst pixels, warp dst patch back to TILE square."""
    x0, y0 = i * TILE, j * TILE
    corners_src = [(x0, y0), (x0 + TILE, y0), (x0 + TILE, y0 + TILE), (x0, y0 + TILE)]  # px
    corners_geo = [src_tf * (x, y) for x, y in corners_src]
    corners_dst_geo = [tr.transform(gx, gy) for gx, gy in corners_geo]
    corners_dst_px = [~dst_tf * (gx, gy) for gx, gy in corners_dst_geo]
    src_pts = np.float32([[0, 0], [TILE, 0], [TILE, TILE], [0, TILE]])
    dst_pts = np.float32([[px, py] for px, py in corners_dst_px])
    # homography from tile-square -> dst pixels, then inverse-warp dst patch
    H = cv2.getPerspectiveTransform(src_pts, dst_pts)
    patch = cv2.warpPerspective(wrp, H, (TILE, TILE), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return patch, corners_dst_px


tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

results = []
# scan a few tiles (center + mid + corner)
tiles = [(3, 3), (4, 3), (3, 2), (1, 1), (0, 0), (6, 4), (7, 5), (2, 6)]
for i, j in tiles:
    if i * TILE >= sw or j * TILE >= sh:
        continue
    try:
        patch, corners = warp_tile_back(i, j)
        patch_rgb = np.repeat(patch[:, :, None], 3, axis=2)
        bits, present, schema = tm.decode(Image.fromarray(patch_rgb, mode="RGB"), MODE="binary")
        value = int(bits[:32], 2) if present and len(bits) >= 32 else None
        ok = value == EXPECTED
        results.append({"tile": (i, j), "ok": ok, "present": present, "value": None if value is None else hex(value), "schema": schema, "corners": [[round(a, 1), round(b, 1)] for a, b in corners]})
    except Exception as exc:
        results.append({"tile": (i, j), "ok": False, "error": repr(exc)})
    print(json.dumps(results[-1], ensure_ascii=False), flush=True)
passed = sum(1 for r in results if r.get("ok"))
print(json.dumps({"passed": passed, "total": len(results)}), flush=True)
