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
OUT = ROOT / "runtime" / "trustmark_full_tiled"

with rasterio.open(BASE) as ds:
    arr = ds.read(1)
    profile = ds.profile.copy()
    h, w = arr.shape

from rasterio.warp import calculate_default_transform, reproject, Resampling
with rasterio.open(BASE) as ds:
    t, nw2, nh2 = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
    wrp = np.empty((nh2, nw2), dtype=np.uint8)
    reproject(source=arr, destination=wrp, src_transform=ds.transform, src_crs=ds.crs, dst_transform=t, dst_crs="EPSG:4326", resampling=Resampling.bilinear)
wrp_rgb = np.repeat(wrp[:, :, None], 3, axis=2)
img = Image.fromarray(wrp_rgb, mode="RGB")
print(json.dumps({"reproj_size": list(img.size)}), flush=True)

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)
# 1) DETECTFIRST on full reprojected image
try:
    boxes = tm.localize(img, return_all=True)
    print(json.dumps({"n_boxes_full_detect": 0 if boxes is None else len(boxes),
                      "boxes": "None" if boxes is None else [[round(v, 3) for v in b] for b in boxes][:5]}), flush=True)
    if boxes:
        for i, bbox in enumerate(boxes[:5]):
            x1 = int(bbox[0] * img.size[0]); y1 = int(bbox[1] * img.size[1])
            x2 = int(bbox[2] * img.size[0]); y2 = int(bbox[3] * img.size[1])
            sub = img.crop((max(0,x1), max(0,y1), min(img.size[0],x2), min(img.size[1],y2)))
            bits, present, schema = tm.decode(sub.convert("RGB"), MODE="binary")
            value = int(bits[:32], 2) if present and len(bits) >= 32 else None
            print(json.dumps({"box": i, "bbox": bbox, "present": present, "value": None if value is None else hex(value), "schema": schema}), flush=True)
except Exception as exc:
    print(json.dumps({"detect_error": repr(exc)}), flush=True)
