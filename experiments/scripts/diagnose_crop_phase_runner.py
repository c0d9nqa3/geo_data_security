"""诊断: center_crop75 图 DETECTFIRST 为何失败 + 网格相位真相。"""
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

SRC = ROOT / "runtime" / "runner_real_b1" / "B1_runner_marked.tif"
EXPECTED = 0xA5A5F00D

with rasterio.open(SRC) as ds:
    arr = ds.read(1)
    h, w = arr.shape
rgb = np.repeat(arr[:, :, None], 3, axis=2)
img = Image.fromarray(rgb, mode="RGB")
crop_box = (int(w * 0.125), int(h * 0.125), int(w * 0.875), int(h * 0.875))
print("crop box:", crop_box, "phase mod1024:", (crop_box[0] % 1024, crop_box[1] % 1024))
crop = img.crop(crop_box)
cw, ch = crop.size
print("crop size:", crop.size)

tm_det = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)
tm_plain = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

# 1) DETECTFIRST whole crop
bits, present, schema = tm_det.decode(crop.convert("RGB"), MODE="binary", DETECTFIRST=True)
print("1) DETECTFIRST:", {"present": present, "schema": schema, "bits32": None if not present else hex(int(bits[:32], 2))})

# 2) phase-aligned manual window: tile grid phase = (-x0) mod 1024
for phase_x in [0, 11, 1035 % 1024]:
    pass
# compute where embedded tile boundaries sit in crop coords: orig boundary b=1024k -> crop x=b-x0
x0, y0, _, _ = crop_box
print("tile boundaries in crop x:", [1024 * k - x0 for k in range(1, 9) if 0 <= 1024 * k - x0 < cw][:6])
bx = 1024 * 1 - x0  # first boundary
print("first boundary:", bx)
# window aligned just after boundary
for wx in [bx, bx + 1, (1024 - x0 % 1024) % 1024]:
    wy = (1024 - y0 % 1024) % 1024
    if 0 <= wx + 1024 <= cw and 0 <= wy + 1024 <= ch:
        patch = crop.crop((wx, wy, wx + 1024, wy + 1024))
        bits, present, schema = tm_plain.decode(patch.convert("RGB"), MODE="binary")
        print(f"2) aligned window ({wx},{wy}):", {"present": present, "value": None if not present else hex(int(bits[:32], 2))})
