"""Scene-level robustness matrix for a TrustMark tiled GeoTIFF band.
Usage: run_scene_matrix_band.py <path_to_watermarked_tif> [band_label]
"""
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
TILE = 1024
BASE_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"
LABEL = sys.argv[2] if len(sys.argv) > 2 else BASE_PATH.stem
OUT = ROOT / "runtime" / "trustmark_scene_matrix"
OUT.mkdir(parents=True, exist_ok=True)

with rasterio.open(BASE_PATH) as ds:
    src_arr = ds.read(1)
    src_crs = ds.crs
    src_tf = ds.transform
h, w = src_arr.shape

tm_det = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)
tm_plain = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

def dec_ok(tm, img, detectfirst=False):
    bits, present, schema = tm.decode(img.convert("RGB"), MODE="binary", DETECTFIRST=detectfirst)
    return present and len(bits) >= 32 and int(bits[:32], 2) == EXPECTED

def union_decode(img, tile_px, max_windows=72):
    tw, th = img.size
    win = max(224, int(tile_px))
    attempts = 0
    if tw >= 224 and th >= 224:
        attempts += 1
        if dec_ok(tm_det, img, detectfirst=True):
            return True, attempts, ("detect", None)
    cands = []
    for gy in range(0, th - win + 1, win):
        for gx in range(0, tw - win + 1, win):
            cands.append((gx, gy, 0))
    step = max(96, win // 8)
    for gy in range(0, th - win + 1, step):
        for gx in range(0, tw - win + 1, step):
            cands.append((gx, gy, 1))
    seen, uniq = set(), []
    for c in cands:
        if c[:2] not in seen:
            seen.add(c[:2]); uniq.append(c)
    uniq.sort(key=lambda c: abs(c[0] + win / 2 - tw / 2) + abs(c[1] + win / 2 - th / 2))
    for x, y, prong in uniq:
        if attempts >= max_windows:
            break
        attempts += 1
        if dec_ok(tm_plain, img.crop((x, y, x + win, y + win))):
            return True, attempts, (f"win_p{prong}", (x, y, win))
    return False, attempts, None

rows = []
def run(name, img, tile_px):
    s = time.perf_counter()
    ok, attempts, where = union_decode(img, tile_px)
    rows.append({"scenario": name, "ok": ok, "attempts": attempts, "hit": where, "seconds": round(time.perf_counter() - s, 1), "size": list(img.size)})
    print(json.dumps(rows[-1], ensure_ascii=False), flush=True)

rgb = np.repeat(src_arr[:, :, None], 3, axis=2)
marked = Image.fromarray(rgb, mode="RGB")

for name, frac, rng in [("crop25_rnd_a", .25, (1234, 987)), ("crop25_rnd_b", .25, (3111, 2888)), ("crop25_rnd_c", .25, (500, 4000)), ("crop75_rnd_a", .75, (500, 400)), ("crop75_rnd_b", .75, (2500, 3000)), ("crop75_rnd_c", .75, (300, 3500))]:
    cw, ch = int(w * frac), int(h * frac)
    x0 = min(rng[0], w - cw); y0 = min(rng[1], h - ch)
    run(name, marked.crop((x0, y0, x0 + cw, y0 + ch)), TILE)
for frac in [.25, .5, .75]:
    cw, ch = int(w * frac), int(h * frac)
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    run(f"crop_center{int(frac*100)}", marked.crop((x0, y0, x0 + cw, y0 + ch)), TILE)
for scale in [.25, .5, .75, 1.25]:
    run(f"resize_{int(scale*100)}", marked.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR), int(TILE * scale))
jp = OUT / f"jpeg_{LABEL}.jpg"; marked.save(jp, "JPEG", quality=90)
run("jpeg_q90", Image.open(jp), TILE)
run("png_convert", marked.convert("RGB"), TILE)
for k, seed in enumerate([123, 7, 999]):
    rng2 = np.random.default_rng(seed)
    noisy = np.clip(rgb.astype(np.int16) + rng2.normal(0, 2, rgb.shape), 0, 255).astype(np.uint8)
    run(f"noise_sigma2_b{k}", Image.fromarray(noisy, mode="RGB"), TILE)
run("gaussian", marked.filter(ImageFilter.GaussianBlur(1.0)), TILE)
run("median", marked.filter(ImageFilter.MedianFilter(3)), TILE)
from rasterio.warp import calculate_default_transform, reproject, Resampling
with rasterio.open(BASE_PATH) as ds:
    t1, w1, h1 = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
    a1 = np.empty((h1, w1), dtype=np.uint8)
    reproject(source=ds.read(1), destination=a1, src_transform=ds.transform, src_crs=ds.crs, dst_transform=t1, dst_crs="EPSG:4326", resampling=Resampling.bilinear)
    a2 = np.empty((h, w), dtype=np.uint8)
    reproject(source=a1, destination=a2, src_transform=t1, src_crs="EPSG:4326", dst_transform=src_tf, dst_crs=src_crs, resampling=Resampling.bilinear)
    run("reproject_4326_attack", Image.fromarray(np.repeat(a2[:, :, None], 3, axis=2), mode="RGB"), TILE)

report = OUT / f"report_scene_{LABEL}.json"
report.write_text(json.dumps({"expected": hex(EXPECTED), "band": LABEL, "results": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
passed = sum(1 for r in rows if r["ok"])
print(json.dumps({"band": LABEL, "passed": passed, "total": len(rows), "rate": round(passed / len(rows), 3), "report": str(report)}), flush=True)
