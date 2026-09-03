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
SRC = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")
OUT = ROOT / "runtime" / "trustmark_full_tiled"
OUT.mkdir(parents=True, exist_ok=True)

TILE = 1024
with rasterio.open(SRC) as ds:
    data = ds.read(1)
    profile = ds.profile.copy()
    h, w = data.shape

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)
payload = format(EXPECTED, "032b")
full = np.repeat(data[:, :, None], 3, axis=2)
marked = np.empty_like(full)

started = time.perf_counter()
count = 0
for ty in range(0, h, TILE):
    for tx in range(0, w, TILE):
        y2, x2 = min(ty + TILE, h), min(tx + TILE, w)
        tile = Image.fromarray(full[ty:y2, tx:x2], mode="RGB")
        enc = tm.encode(tile, payload, MODE="binary", WM_STRENGTH=1.0)
        marked[ty:y2, tx:x2] = np.asarray(enc)
        count += 1
        if count % 8 == 0:
            print(json.dumps({"embedded": count, "seconds": round(time.perf_counter() - started, 1)}), flush=True)
print(json.dumps({"embedded_total": count, "seconds": round(time.perf_counter() - started, 1)}), flush=True)

wm_tif = OUT / "B1_full_tiled.tif"
with rasterio.open(wm_tif, "w", **profile) as ds:
    ds.write(marked[:, :, 0].astype(np.uint8), 1)
    ds.update_tags(GDS_ENGINE="TrustMark-Q-TILED1024", GDS_ECC="BCH_SUPER")
print(json.dumps({"saved": str(wm_tif)}), flush=True)
orig = full.astype(np.float64); mk = marked.astype(np.float64)
mse = float(np.mean((orig - mk) ** 2))
psnr = float("inf") if mse == 0 else 20 * np.log10(255 / np.sqrt(mse))
print(json.dumps({"psnr_db": psnr}), flush=True)
