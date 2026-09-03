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

SRC_DIR = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00")
OUT = ROOT / "runtime" / "trustmark_full_tiled"
OUT.mkdir(parents=True, exist_ok=True)
TILE = 1024
EXPECTED = 0xA5A5F00D
payload = format(EXPECTED, "032b")

tm = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

summary = {}
for band in range(2, 8):
    src = SRC_DIR / f"LT51470342011231KHC00_B{band}.TIF"
    dst = OUT / f"B{band}_full_tiled.tif"
    if not src.exists():
        summary[band] = "missing"
        continue
    with rasterio.open(src) as ds:
        data = ds.read(1)
        profile = ds.profile.copy()
        h, w = data.shape
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
    with rasterio.open(dst, "w", **profile) as ds:
        ds.write(marked[:, :, 0].astype(np.uint8), 1)
        ds.update_tags(GDS_ENGINE="TrustMark-Q-TILED1024", GDS_ECC="BCH_SUPER")
    mse = float(np.mean((full.astype(np.float64) - marked.astype(np.float64)) ** 2))
    psnr = float("inf") if mse == 0 else 20 * np.log10(255 / np.sqrt(mse))
    summary[band] = {"tiles": count, "seconds": round(time.perf_counter() - started, 1), "psnr_db": round(psnr, 2)}
    print(json.dumps({"band": band, **summary[band]}), flush=True)
(OUT / "embed_summary_b2b7.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary), flush=True)
