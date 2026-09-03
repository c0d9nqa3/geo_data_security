"""复刻 v3 场景矩阵的精确裁剪坐标, 验证 DETECTFIRST 稳定性。"""
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

EXPECTED = 0xA5A5F00D
tm = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)

path = ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"
with rasterio.open(path) as ds:
    arr = ds.read(1)
    h, w = arr.shape
rgb = np.repeat(arr[:, :, None], 3, axis=2)
img = Image.fromarray(rgb, mode="RGB")

# exact v3 boxes (v3 script uses cw,ch = int(w*frac),int(h*frac); x0=(w-cw)//2)
cases = {}
for frac in [0.25, 0.5, 0.75]:
    cw, ch = int(w * frac), int(h * frac)
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    cases[f"center{int(frac*100)}_v3box"] = (x0, y0, x0 + cw, y0 + ch)
# my diag box (int(w*0.125) style)
cases["center75_mydiag"] = (int(w * 0.125), int(h * 0.125), int(w * 0.875), int(h * 0.875))
for name, box in cases.items():
    crop = img.crop(box)
    bits, present, schema = tm.decode(crop.convert("RGB"), MODE="binary", DETECTFIRST=True)
    val = int(bits[:32], 2) if present and len(bits) >= 32 else None
    print(f"{name} box={box}: DETECTFIRST present={present} value={None if val is None else hex(val)} schema={schema}")
