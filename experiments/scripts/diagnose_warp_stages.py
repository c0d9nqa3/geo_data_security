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
i, j = 3, 3  # center tile

with rasterio.open(BASE) as ds:
    src_arr = ds.read(1)
    src_crs, src_tf = ds.crs, ds.transform

from rasterio.warp import calculate_default_transform, reproject, Resampling
with rasterio.open(BASE) as ds:
    dst_tf, nw2, nh2 = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
    wrp = np.empty((nh2, nw2), dtype=np.uint8)
    reproject(source=src_arr, destination=wrp, src_transform=ds.transform, src_crs=ds.crs,
              dst_transform=dst_tf, dst_crs="EPSG:4326", resampling=Resampling.bilinear)

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

def dec(a):
    rgb = np.repeat(a[:, :, None], 3, axis=2)
    bits, present, schema = tm.decode(Image.fromarray(rgb, mode="RGB"), MODE="binary")
    value = int(bits[:32], 2) if present and len(bits) >= 32 else None
    return {"present": present, "value": None if value is None else hex(value), "schema": schema}

# 1) original tile straight from marked source
t0 = src_arr[j*TILE:(j+1)*TILE, i*TILE:(i+1)*TILE]
r1 = dec(t0)
print(json.dumps({"1_direct_tile": r1}), flush=True)

# 2) simulate warp-back error on a pure affine: scale x1.115 y0.888 (like reproj), then warp back
M = cv2.getRotationMatrix2D((TILE/2, TILE/2), 0, 1.0)
M[0,0], M[1,1] = 1.115, 0.888
warped_aff = cv2.warpAffine(t0, M, (int(TILE*1.115), int(TILE*0.888)), flags=cv2.INTER_LINEAR)
back = cv2.warpAffine(warped_aff, np.linalg.inv(np.vstack([M, [0,0,1]]))[:2], (TILE, TILE), flags=cv2.INTER_LINEAR)
r2 = dec(back)
print(json.dumps({"2_affine_roundtrip": r2}), flush=True)

# 3) crop the reprojected area of tile (3,3) from wrp by its corner quad bbox, then perspective-warp back
tr = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
x0, y0 = i*TILE, j*TILE
corners_src = [(x0, y0), (x0+TILE, y0), (x0+TILE, y0+TILE), (x0, y0+TILE)]
corners_dst = [~dst_tf * tr.transform(*(src_tf * (x, y))) for x, y in corners_src]
src_pts = np.float32([[0,0],[TILE,0],[TILE,TILE],[0,TILE]])
dst_pts = np.float32([[px,py] for px,py in corners_dst])
H = cv2.getPerspectiveTransform(src_pts, dst_pts)
patch = cv2.warpPerspective(wrp, H, (TILE, TILE), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
r3 = dec(patch)
print(json.dumps({"3_persp_warpback": r3, "corners": [[round(a,1),round(b,1)] for a,b in corners_dst]}), flush=True)

# 4) same but nearest-neighbor to rule out interpolation loss
patch_nn = cv2.warpPerspective(wrp, H, (TILE, TILE), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
r4 = dec(patch_nn)
print(json.dumps({"4_persp_warpback_nn": r4}), flush=True)
