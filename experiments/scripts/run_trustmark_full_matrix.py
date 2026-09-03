from pathlib import Path
import sys
import json
import time

import numpy as np
import rasterio
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

EXPECTED = 0xA5A5F00D
BASE = ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"
OUT = ROOT / "runtime" / "trustmark_full_tiled"
OUT.mkdir(parents=True, exist_ok=True)

with rasterio.open(BASE) as ds:
    arr = ds.read(1)
    profile = ds.profile.copy()
    h, w = arr.shape
rgb = np.repeat(arr[:, :, None], 3, axis=2)
marked = Image.fromarray(rgb, mode="RGB")
print(json.dumps({"size": [w, h]}), flush=True)

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)

def decode_bits(img):
    bits, present, schema = tm.decode(img.convert("RGB"), MODE="binary", DETECTFIRST=True)
    value = int(bits[:32], 2) if present and len(bits) >= 32 else None
    return value, present, schema

def scenario(name, img):
    started = time.perf_counter()
    try:
        value, present, schema = decode_bits(img)
        return {"scenario": name, "ok": value == EXPECTED, "value": None if value is None else hex(value), "present": present, "schema": schema, "seconds": round(time.perf_counter() - started, 3), "size": list(img.size)}
    except Exception as exc:
        return {"scenario": name, "ok": False, "error": repr(exc)}

rows = []
rows.append(scenario("full", marked))
# random-position crops 25% and 75% of full image
for name, frac, rng in [("crop25_a", .25, (1234, 987)), ("crop25_b", .25, (3333, 2222)), ("crop75_a", .75, (500, 400)), ("crop75_b", .75, (2500, 3000))]:
    x0, y0 = rng
    cw, ch = int(w * frac), int(h * frac)
    x0 = min(x0, w - cw); y0 = min(y0, h - ch)
    rows.append(scenario(name, marked.crop((x0, y0, x0 + cw, y0 + ch))))
# center crops
for name, frac in [("crop_center25", .25), ("crop_center75", .75)]:
    cw, ch = int(w * frac), int(h * frac)
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    rows.append(scenario(name, marked.crop((x0, y0, x0 + cw, y0 + ch))))
# scales
for scale in [.25, .5, .75, 1.25]:
    rows.append(scenario(f"resize_{int(scale*100)}", marked.resize((max(64, int(w*scale)), max(64, int(h*scale))), Image.Resampling.BILINEAR)))
# jpeg
jp = OUT / "jpeg_q90.jpg"; marked.convert("RGB").save(jp, "JPEG", quality=90)
rows.append(scenario("jpeg_q90", Image.open(jp)))
# noise
rng = np.random.default_rng(123)
noisy = np.clip(rgb.astype(np.int16) + rng.normal(0, 2, rgb.shape), 0, 255).astype(np.uint8)
rows.append(scenario("noise_sigma2", Image.fromarray(noisy, mode="RGB")))
# filters
rows.append(scenario("gaussian", marked.filter(ImageFilter.GaussianBlur(1.0))))
rows.append(scenario("median", marked.filter(ImageFilter.MedianFilter(3))))
# reproject: warp to EPSG:4326 and back (resampling transform attack)
from rasterio.warp import calculate_default_transform, reproject, Resampling
with rasterio.open(BASE) as ds:
    dst_crs = "EPSG:4326"
    transform, nw, nh = calculate_default_transform(ds.crs, dst_crs, ds.width, ds.height, *ds.bounds)
    warped = np.empty((nh, nw), dtype=np.uint8)
    reproject(source=arr, destination=warped, src_transform=ds.transform, src_crs=ds.crs, dst_transform=transform, dst_crs=dst_crs, resampling=Resampling.bilinear)
warped_rgb = np.repeat(warped[:, :, None], 3, axis=2)
rows.append(scenario("reproject_4326", Image.fromarray(warped_rgb, mode="RGB")))
# reproject back to 32644
with rasterio.open(BASE) as ds:
    back_t, bw, bh = calculate_default_transform("EPSG:4326", ds.crs, nw, nh, *rasterio.transform.array_bounds(nh, nw, transform))
    back = np.empty((bh, bw), dtype=np.uint8)
    reproject(source=warped, destination=back, src_transform=transform, src_crs=dst_crs, dst_transform=back_t, dst_crs=ds.crs, resampling=Resampling.bilinear)
back_rgb = np.repeat(back[:, :, None], 3, axis=2)
rows.append(scenario("reproject_roundtrip", Image.fromarray(back_rgb, mode="RGB")))

for r in rows:
    print(json.dumps(r, ensure_ascii=False), flush=True)
(OUT / "report_matrix.json").write_text(json.dumps({"expected": hex(EXPECTED), "results": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
passed = sum(1 for r in rows if r.get("ok"))
print(json.dumps({"passed": passed, "total": len(rows), "rate": round(passed / len(rows), 3)}), flush=True)
