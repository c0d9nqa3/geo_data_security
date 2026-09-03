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
TILE = 1024

with rasterio.open(BASE) as ds:
    src_crs = ds.crs
    tf_src = ds.transform
    sw, sh = ds.width, ds.height

from rasterio.warp import calculate_default_transform, reproject, Resampling
with rasterio.open(BASE) as ds:
    t4326, w4326, h4326 = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
    a4326 = np.empty((h4326, w4326), dtype=np.uint8)
    reproject(source=ds.read(1), destination=a4326, src_transform=ds.transform, src_crs=ds.crs,
              dst_transform=t4326, dst_crs="EPSG:4326", resampling=Resampling.bilinear)

tr_fwd = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)


def tile_quad_4326(i, j):
    x0, y0 = i * TILE, j * TILE
    pts = []
    for cx, cy in [(x0, y0), (x0 + TILE, y0), (x0 + TILE, y0 + TILE), (x0, y0 + TILE)]:
        gx, gy = tf_src * (cx, cy)
        lon, lat = tr_fwd.transform(gx, gy)
        px, py = ~t4326 * (lon, lat)
        pts.append((px, py))
    return pts


rows = []
tiles = [(3, 3), (4, 3), (3, 2), (2, 2), (5, 4), (1, 1), (6, 5), (3, 4), (4, 4), (5, 3)]
for i, j in tiles:
    try:
        quad = tile_quad_4326(i, j)
        dst_pts = np.float32([[0, 0], [TILE, 0], [TILE, TILE], [0, TILE]])
        src_pts = np.float32(quad)
        # H maps quad(source in 4326 img) -> tile square. warpPerspective needs src->dst map M,
        # and samples src at M^-1(dst) internally... actually warpPerspective(src, M, dsize):
        # dst(x,y) sampled from src at M^-1*(x,y) -> M must map dst->src? Test both directions.
        H = cv2.getPerspectiveTransform(src_pts, dst_pts)  # quad->square
        # cv2.warpPerspective(src_img, M, ...) : for dst pixel p, sample src at M^-1 p.
        # We want dst=square, src=4326img: sample 4326img at quad coords of square pixel -> need M = quad->square
        # i.e. p_square -> M p_square = quad position? NO: sample src at M^-1(p). p is in square coords.
        # M^-1 maps square->quad position in 4326img. So M = square->quad = inv(quad->square).
        H2 = np.linalg.inv(H)
        patch = cv2.warpPerspective(a4326, H2, (TILE, TILE), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        bits, present, schema = tm.decode(Image.fromarray(np.repeat(patch[:, :, None], 3, axis=2), mode="RGB"), MODE="binary")
        value = int(bits[:32], 2) if present and len(bits) >= 32 else None
        rows.append({"tile": (i, j), "ok": value == EXPECTED, "present": present, "value": None if value is None else hex(value), "schema": schema, "quad": [[round(a,1), round(b,1)] for a, b in quad]})
    except Exception as exc:
        rows.append({"tile": (i, j), "ok": False, "error": repr(exc)})
    print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
print(json.dumps({"passed": sum(1 for r in rows if r.get("ok")), "total": len(rows)}), flush=True)
