from pathlib import Path
import sys
import json

import numpy as np
import rasterio
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

EXPECTED = 0xA5A5F00D
BASE = ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"
OUT = ROOT / "runtime" / "trustmark_scene_matrix"
OUT.mkdir(parents=True, exist_ok=True)
TILE = 1024

# remove ALL custom GDS_* tags and rewrite; keep standard georeferencing (external-software tag stripping simulation)
with rasterio.open(BASE) as ds:
    arr = ds.read(1)
    profile = ds.profile.copy()
    keep = {k: v for k, v in ds.tags().items() if not k.startswith("GDS_")}
stripped = OUT / "B1_full_tiled_notags.tif"
with rasterio.open(stripped, "w", **profile) as ds:
    ds.update_tags(**keep)
    ds.write(arr, 1)
with rasterio.open(stripped) as ds:
    tags = ds.tags()
print(json.dumps({"custom_tags_remaining": [k for k in tags if k.startswith("GDS_")], "kept_standard": [k for k in tags if not k.startswith("GDS_")][:8]}), flush=True)

rgb = np.repeat(arr[:, :, None], 3, axis=2)
marked = Image.fromarray(rgb, mode="RGB")

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

import time
rows = []
# full image, no tags
s = time.perf_counter()
ok, att, where = union_decode(marked, TILE)
rows.append({"scenario": "notags_full", "ok": ok, "attempts": att, "hit": where, "seconds": round(time.perf_counter() - s, 1)})
print(json.dumps(rows[-1]), flush=True)
# crops from the no-tag image (simulates: stripped tags + crop)
w, h = marked.size
for name, frac, rng in [("notags_crop25", .25, (1234, 987)), ("notags_crop75", .75, (2500, 3000))]:
    cw, ch = int(w * frac), int(h * frac)
    x0 = min(rng[0], w - cw); y0 = min(rng[1], h - ch)
    s = time.perf_counter()
    ok, att, where = union_decode(marked.crop((x0, y0, x0 + cw, y0 + ch)), TILE)
    rows.append({"scenario": name, "ok": ok, "attempts": att, "hit": where, "seconds": round(time.perf_counter() - s, 1)})
    print(json.dumps(rows[-1]), flush=True)
# strip tags + resize 25%
for scale in [.25, .75]:
    s = time.perf_counter()
    img = marked.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)
    ok, att, where = union_decode(img, int(TILE * scale))
    rows.append({"scenario": f"notags_resize{int(scale*100)}", "ok": ok, "attempts": att, "hit": where, "seconds": round(time.perf_counter() - s, 1)})
    print(json.dumps(rows[-1]), flush=True)

print(json.dumps({"passed": sum(1 for r in rows if r["ok"]), "total": len(rows)}), flush=True)
(OUT / "report_notags_b1.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
