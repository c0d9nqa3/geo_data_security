"""真实 B1 全幅 runner 验证：embed -> 攻击(裁剪/缩放) -> extract。"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "runtime" / "trustmark_venv" / "Scripts" / "python.exe"
RUNNER = ROOT / "server2" / "pipeline" / "geo_security" / "trustmark_geotiff_runner.py"
SRC = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")
EXPECTED = 0xA5A5F00D
tmp = ROOT / "runtime" / "runner_real_b1"
tmp.mkdir(parents=True, exist_ok=True)
marked = tmp / "B1_runner_marked.tif"


def run(args):
    p = subprocess.run([str(PYTHON), str(RUNNER), *args], capture_output=True, text=True, encoding="utf-8", timeout=1800)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip()[-800:] or p.stdout.strip()[-800:])
    return json.loads(p.stdout.strip().splitlines()[-1])


if not marked.exists():
    print(json.dumps({"phase": "embed", **run(["embed", str(SRC), str(marked), format(EXPECTED, "08X")])}), flush=True)
else:
    print(json.dumps({"phase": "embed", "skipped": "exists"}), flush=True)

with rasterio.open(marked) as ds:
    arr = ds.read(1)
    profile = ds.profile.copy()
    h, w = arr.shape
rgb = np.repeat(arr[:, :, None], 3, axis=2)
img = Image.fromarray(rgb, mode="RGB")

outcomes = []
def check(name, pil_img, temp_path):
    pil_img.save(temp_path, format="PNG")
    res = run(["extract", str(temp_path), format(EXPECTED, "08X")])
    ok = bool(res.get("detected"))
    outcomes.append({"scenario": name, "ok": ok, **res})
    print(json.dumps(outcomes[-1], ensure_ascii=False), flush=True)

check("full", img, tmp / "full.png")
cw, ch = int(w * 0.25), int(h * 0.25)
check("random_crop25", img.crop((1234, 987, 1234 + cw, 987 + ch)), tmp / "crop25.png")
check("resize25", img.resize((int(w * 0.25), int(h * 0.25)), Image.Resampling.BILINEAR), tmp / "resize25.png")
check("resize75", img.resize((int(w * 0.75), int(h * 0.75)), Image.Resampling.BILINEAR), tmp / "resize75.png")
jp = tmp / "q90.jpg"
img.save(jp, "JPEG", quality=90)
check("jpeg_q90", Image.open(jp).convert("RGB"), tmp / "q90_png.png")
check("center_crop75", img.crop((int(w*.125), int(h*.125), int(w*.875), int(h*.875))), tmp / "crop75.png")

passed = sum(1 for o in outcomes if o["ok"])
print(json.dumps({"passed": passed, "total": len(outcomes)}), flush=True)
(tmp / "report.json").write_text(json.dumps(outcomes, ensure_ascii=False, indent=2), encoding="utf-8")
