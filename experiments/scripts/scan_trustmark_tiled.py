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
TILE = 1024  # embed tile size at full resolution

with rasterio.open(BASE) as ds:
    arr = ds.read(1)
    profile = ds.profile.copy()
    h, w = arr.shape
rgb = np.repeat(arr[:, :, None], 3, axis=2)
marked = Image.fromarray(rgb, mode="RGB")

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=False)


def decode_win(img):
    bits, present, schema = tm.decode(img.convert("RGB"), MODE="binary")
    if present and len(bits) >= 32 and int(bits[:32], 2) == EXPECTED:
        return True
    return False


def scan_decode(img, tile_px, max_windows=80):
    """Grid-aligned sliding-window scan. tile_px = embedded tile size in THIS image's pixels.
    Candidate windows are centered on the tile grid so each window covers ONE tile."""
    tw, th = img.size
    win = max(224, int(tile_px))
    # grid origins in attacked-image pixels (tile grid may be shifted by rounding)
    grid_origins = []
    for origin in (0, 1, -1, 2, -2):  # tolerate 1-2 px rounding from resize/reproject
        grid_origins.append(origin % max(1, win))
    centers = []
    for gox in grid_origins:
        for goy in grid_origins:
            # window whose CENTER sits at grid point => covers one tile body
            for gy in range(goy - win, th + win, win):
                for gx in range(gox - win, tw + win, win):
                    x = gx
                    y = gy
                    if 0 <= x < tw and 0 <= y < th and x + win <= tw and y + win <= th:
                        centers.append((x, y, gox, goy))
    # dedupe
    seen = set()
    uniq = []
    for c in centers:
        k = (c[0], c[1])
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    # try windows whose center is closest to image center first
    uniq.sort(key=lambda c: abs(c[0] + win / 2 - tw / 2) + abs(c[1] + win / 2 - th / 2))
    attempts = 0
    for x, y, gox, goy in uniq:
        if attempts >= max_windows:
            break
        patch = img.crop((x, y, x + win, y + win))
        attempts += 1
        if decode_win(patch):
            return True, attempts, (x, y, win, gox, goy)
    return False, attempts, None


def make_variants():
    vs = {}
    rng2 = np.random.default_rng(123)
    noisy = np.clip(rgb.astype(np.int16) + rng2.normal(0, 2, rgb.shape), 0, 255).astype(np.uint8)
    vs["noise_sigma2"] = Image.fromarray(noisy, mode="RGB")
    vs["gaussian"] = marked.filter(ImageFilter.GaussianBlur(1.0))
    vs["median"] = marked.filter(ImageFilter.MedianFilter(3))
    jp = OUT / "scan_jpeg_q90.jpg"
    marked.convert("RGB").save(jp, "JPEG", quality=90)
    vs["jpeg_q90"] = Image.open(jp)
    for scale in [.25, .5, .75, 1.25]:
        vs[f"resize_{int(scale*100)}"] = marked.resize((max(64, int(w * scale)), max(64, int(h * scale))), Image.Resampling.BILINEAR)
    # reproject to 4326 and roundtrip
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    with rasterio.open(BASE) as ds:
        t, nw2, nh2 = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
        wrp = np.empty((nh2, nw2), dtype=np.uint8)
        reproject(source=arr, destination=wrp, src_transform=ds.transform, src_crs=ds.crs, dst_transform=t, dst_crs="EPSG:4326", resampling=Resampling.bilinear)
    vs["reproject_4326"] = Image.fromarray(np.repeat(wrp[:, :, None], 3, axis=2), mode="RGB")
    return vs


def estimate_tile(img):
    """tile size in attacked-image pixels: scale factor relative to full size."""
    tw, th = img.size
    s = max(tw / w, th / h)
    return max(224, int(TILE * s))


vs = make_variants()
# full image itself also scanned
vs["full"] = marked
rows = []
for name, img in vs.items():
    tile_px = estimate_tile(img)
    started = time.perf_counter()
    ok, attempts, where = scan_decode(img, tile_px)
    rows.append({"scenario": name, "ok": ok, "attempts": attempts, "window": where, "tile_px": tile_px, "seconds": round(time.perf_counter() - started, 1), "size": list(img.size)})
    print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
(OUT / "report_scan.json").write_text(json.dumps({"expected": hex(EXPECTED), "results": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"passed": sum(1 for r in rows if r["ok"]), "total": len(rows)}), flush=True)
