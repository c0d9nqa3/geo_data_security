"""对比: 两个嵌入版本 (实验 B1_full_tiled vs runner B1_runner_marked) 的裁剪图 DETECTFIRST。"""
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

for label, path in [
    ("exp_full_tiled", ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"),
    ("runner_marked", ROOT / "runtime" / "runner_real_b1" / "B1_runner_marked.tif"),
]:
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        h, w = arr.shape
    rgb = np.repeat(arr[:, :, None], 3, axis=2)
    img = Image.fromarray(rgb, mode="RGB")
    crop = img.crop((int(w * 0.125), int(h * 0.125), int(w * 0.875), int(h * 0.875)))
    bits, present, schema = tm.decode(crop.convert("RGB"), MODE="binary", DETECTFIRST=True)
    val = int(bits[:32], 2) if present and len(bits) >= 32 else None
    print(f"{label}: detectfirst present={present} value={None if val is None else hex(val)} schema={schema}")
    # also plain decode of full (no crop)
    bits2, p2, _ = tm.decode(img.convert("RGB"), MODE="binary", DETECTFIRST=False)
    v2 = int(bits2[:32], 2) if p2 and len(bits2) >= 32 else None
    print(f"   full plain decode: present={p2} value={None if v2 is None else hex(v2)}")
