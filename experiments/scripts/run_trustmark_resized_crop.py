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
BASE = ROOT / "runtime" / "trustmark_matrix_b1" / "watermarked.tif"
OUT = ROOT / "runtime" / "trustmark_crop_b1"
OUT.mkdir(parents=True, exist_ok=True)

with rasterio.open(BASE) as ds:
    rgb = np.repeat(ds.read(1)[:, :, None], 3, axis=2)
marked = Image.fromarray(rgb, mode="RGB")
w, h = marked.size
print({"source_size": [w, h]}, flush=True)

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)

scenarios = {}
# resized-crop: crop then scale BACK to original size (official training distribution)
for name, box in [
    ("resized_crop_center25", (int(w * .375), int(h * .375), int(w * .625), int(h * .625))),
    ("resized_crop_random25", (int(w * .17), int(h * .31), int(w * .42), int(h * .56))),
    ("resized_crop_center75", (int(w * .125), int(h * .125), int(w * .875), int(h * .875))),
    ("resized_crop_random75", (int(w * .05), int(h * .07), int(w * .80), int(h * .82))),
]:
    patch = marked.crop(box)
    scenarios[name] = patch.resize((w, h), Image.Resampling.BILINEAR)
# plain-crop small patch decode (no scale-back) for reference
scenarios["plain_crop_center25"] = marked.crop((int(w * .375), int(h * .375), int(w * .625), int(h * .625)))

rows = []
for name, image in scenarios.items():
    started = time.perf_counter()
    try:
        bits, present, schema = tm.decode(image.convert("RGB"), MODE="binary", DETECTFIRST=True)
        value = int(bits[:32], 2) if present and len(bits) >= 32 else None
        row = {"scenario": name, "ok": value == EXPECTED, "value": None if value is None else hex(value), "present": present, "schema": schema, "seconds": round(time.perf_counter() - started, 3), "size": list(image.size)}
    except Exception as exc:
        row = {"scenario": name, "ok": False, "error": repr(exc)}
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)
(OUT / "report_resized.json").write_text(json.dumps({"expected": hex(EXPECTED), "results": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
