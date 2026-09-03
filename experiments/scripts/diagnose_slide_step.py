"""诊断: 细步长滑扫能否容忍任意裁剪相位 (center_crop75 相位 (1013,908) mod 1024)。"""
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
crop = img.crop((int(w * 0.125), int(h * 0.125), int(w * 0.875), int(h * 0.875)))
print("crop size:", crop.size)

tm_det = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)
tm_plain = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

boxes = tm_det.localize(crop, return_all=True)
print("localize boxes:", "None" if boxes is None else len(boxes))
cw, ch = crop.size
if boxes:
    for i, bbox in enumerate(boxes[:6]):
        x1 = int(bbox[0] * cw); y1 = int(bbox[1] * ch)
        x2 = int(bbox[2] * cw); y2 = int(bbox[3] * ch)
        x1 = max(0, min(x1, cw - 1)); y1 = max(0, min(y1, ch - 1))
        x2 = max(x1 + 1, min(x2, cw)); y2 = max(y1 + 1, min(y2, ch))
        sub = crop.crop((x1, y1, x2, y2))
        bits, present, schema = tm_plain.decode(sub.convert("RGB"), MODE="binary")
        value = int(bits[:32], 2) if present and len(bits) >= 32 else None
        print(f"box {i}: {[round(v,3) for v in bbox]} -> present={present} value={None if value is None else hex(value)}")
