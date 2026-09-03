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
OUT = ROOT / "runtime" / "trustmark_tiled"
OUT.mkdir(parents=True, exist_ok=True)

TILE = 512
with rasterio.open(SRC) as ds:
    row0 = (ds.height - 1024) // 2
    col0 = (ds.width - 1024) // 2
    data = ds.read(1, window=rasterio.windows.Window(col0, row0, 1024, 1024))
    profile = ds.profile.copy()
    profile.update(width=1024, height=1024, transform=ds.window_transform(rasterio.windows.Window(col0, row0, 1024, 1024)))

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)
payload = format(EXPECTED, "032b")

# Tile-wise embedding: each 512x512 tile carries the same payload independently
full = np.repeat(data[:, :, None], 3, axis=2)
marked_full = full.copy()
for ty in range(0, 1024, TILE):
    for tx in range(0, 1024, TILE):
        tile = Image.fromarray(full[ty:ty + TILE, tx:tx + TILE], mode="RGB")
        enc = tm.encode(tile, payload, MODE="binary", WM_STRENGTH=1.0)
        marked_full[ty:ty + TILE, tx:tx + TILE] = np.asarray(enc)
wm_tif = OUT / "watermarked_tiled_1024.tif"
with rasterio.open(wm_tif, "w", **profile) as ds:
    ds.write(marked_full[:, :, 0].astype(np.uint8), 1)
    ds.update_tags(GDS_ENGINE="TrustMark-Q-TILED512", GDS_ECC="BCH_SUPER")

def decode_bits(img):
    bits, present, schema = tm.decode(img.convert("RGB"), MODE="binary", DETECTFIRST=True)
    value = int(bits[:32], 2) if present and len(bits) >= 32 else None
    return value, present, schema

results = []
w = h = 1024
for name, box in [
    ("tile_aligned_512", (256, 256, 768, 768)),            # exactly one full tile
    ("half_tile_offset_512", (0, 512, 512, 1024)),          # offset by half tile
    ("random_crop25_512", (int(w * .19), int(h * .33), int(w * .19) + 512, int(h * .33) + 512)),
    ("random_crop75", (int(w * .05), int(h * .07), int(w * .80), int(h * .82))),
]:
    patch = marked_full[box[1]:box[3], box[0]:box[2]]
    img = Image.fromarray(patch, mode="RGB")
    started = time.perf_counter()
    value, present, schema = decode_bits(img)
    results.append({"scenario": name, "box": box, "ok": value == EXPECTED, "value": None if value is None else hex(value), "present": present, "schema": schema, "seconds": round(time.perf_counter() - started, 3)})
    print(json.dumps(results[-1], ensure_ascii=False), flush=True)
# whole-image full decode (DETECTFIRST=False also) reference
value, present, schema = decode_bits(Image.fromarray(marked_full, mode="RGB"))
results.append({"scenario": "full_image", "ok": value == EXPECTED, "value": None if value is None else hex(value), "present": present, "schema": schema})
print(json.dumps(results[-1], ensure_ascii=False), flush=True)
# PSNR per band grayscale approximation
orig = full.astype(np.float64); marked = marked_full.astype(np.float64)
mse = float(np.mean((orig - marked) ** 2))
psnr = float("inf") if mse == 0 else 20 * np.log10(255 / np.sqrt(mse))
print(json.dumps({"psnr_db": psnr, "n_tiles": 4, "tile": TILE}, ensure_ascii=False), flush=True)
(OUT / "report.json").write_text(json.dumps({"expected": hex(EXPECTED), "results": results, "psnr_db": psnr}, ensure_ascii=False, indent=2), encoding="utf-8")
