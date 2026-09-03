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
BASE = ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"

with rasterio.open(BASE) as ds:
    arr = ds.read(1)
h, w = arr.shape
rgb = np.repeat(arr[:, :, None], 3, axis=2)
marked = Image.fromarray(rgb, mode="RGB")

# two decoders: with bbox detector for unknown-phase crops, plain for aligned geometries
tm_det = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)
tm_plain = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

def dec_ok(tm, img, detectfirst):
    bits, present, schema = tm.decode(img.convert("RGB"), MODE="binary", DETECTFIRST=detectfirst)
    return present and len(bits) >= 32 and int(bits[:32], 2) == EXPECTED

rows = []
def run(name, img, use_detectfirst=True, max_retries=3):
    s = time.perf_counter()
    tm = tm_det if use_detectfirst else tm_plain
    ok = False
    attempts = 0
    # crop scenario: bbox detector may need a couple of tries on partial tiles; also try plain decode fallback
    for trial in range(max_retries):
        attempts += 1
        if dec_ok(tm, img, use_detectfirst):
            ok = True
            break
        tm = tm_plain if tm is tm_det else tm_det
        use_detectfirst = not use_detectfirst
    if not ok:
        # phase-grid fallback: unknown crop offset -> try windows at 256px phase steps
        tw, th = img.size
        win = 1024
        cands = []
        for phx in range(0, 256):
            for phy in range(0, 256):
                x0 = phx + ((tw // 2 - win // 2 - phx) // 1024) * 1024
                y0 = phy + ((th // 2 - win // 2 - phy) // 1024) * 1024
                if 0 <= x0 and 0 <= y0 and x0 + win <= tw and y0 + win <= th:
                    cands.append((x0, y0, phx, phy))
        # dedupe by (x0,y0), nearest image center first
        seen, uniq = set(), []
        for c in cands:
            if c[:2] not in seen:
                seen.add(c[:2]); uniq.append(c)
        uniq.sort(key=lambda c: abs(c[0] + win/2 - tw/2) + abs(c[1] + win/2 - th/2))
        for x0, y0, _, _ in uniq[:40]:
            attempts += 1
            if dec_ok(tm_plain, img.crop((x0, y0, x0 + win, y0 + win)), False):
                ok = True
                break
    rows.append({"scenario": name, "ok": ok, "attempts": attempts, "seconds": round(time.perf_counter() - s, 2), "size": list(img.size)})
    print(json.dumps(rows[-1], ensure_ascii=False), flush=True)

# random-position crops (25% / 75%), several batches
for name, frac, rng in [("crop25_rnd_a", .25, (1234, 987)), ("crop25_rnd_b", .25, (3111, 2888)), ("crop25_rnd_c", .25, (500, 4000)), ("crop75_rnd_a", .75, (500, 400)), ("crop75_rnd_b", .75, (2500, 3000)), ("crop75_rnd_c", .75, (300, 3500))]:
    cw, ch = int(w * frac), int(h * frac)
    x0 = min(rng[0], w - cw); y0 = min(rng[1], h - ch)
    run(name, marked.crop((x0, y0, x0 + cw, y0 + ch)))
for frac in [.25, .5, .75]:
    cw, ch = int(w * frac), int(h * frac)
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    run(f"crop_center{int(frac*100)}", marked.crop((x0, y0, x0 + cw, y0 + ch)))

(Path(ROOT) / "runtime" / "trustmark_scene_matrix" / "report_crop_detect.json").write_text(json.dumps({"expected": hex(EXPECTED), "results": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"passed": sum(1 for r in rows if r["ok"]), "total": len(rows)}), flush=True)
