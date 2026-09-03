"""Runner 冒烟验证：合成 uint8 GeoTIFF embed -> extract 应检出同一 32bit 值。"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "runtime" / "trustmark_venv" / "Scripts" / "python.exe"
RUNNER = ROOT / "server2" / "pipeline" / "geo_security" / "trustmark_geotiff_runner.py"
EXPECTED = 0x1234ABCD

tmp = ROOT / "runtime" / "runner_smoke"
tmp.mkdir(parents=True, exist_ok=True)
source = tmp / "source.tif"
dest = tmp / "marked.tif"

rng = np.random.default_rng(7)
values = rng.integers(0, 256, (1024, 1024), dtype=np.uint8)
profile = {"driver": "GTiff", "height": 1024, "width": 1024, "count": 1, "dtype": "uint8", "crs": "EPSG:32644", "transform": from_origin(500000, 4000000, 30, 30)}
with rasterio.open(source, "w", **profile) as ds:
    ds.write(values, 1)
    ds.update_tags(AREA_OR_POINT="Area")

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=900)
    print("returncode:", p.returncode)
    if p.stderr.strip():
        print("stderr:", p.stderr.strip()[-500:])
    if p.stdout.strip():
        print("stdout:", p.stdout.strip()[-500:])
    p.check_returncode()
    return json.loads(p.stdout.strip().splitlines()[-1])

print("== embed ==")
embed = run([str(PYTHON), str(RUNNER), "embed", str(source), str(dest), format(EXPECTED, "08X")])
print("embed result:", json.dumps(embed, ensure_ascii=False))

with rasterio.open(dest) as ds:
    print("dest dtype:", ds.dtypes[0], "crs:", ds.crs, "shape:", (ds.height, ds.width))
    print("GDS tags:", {k: v for k, v in ds.tags().items() if k.startswith("GDS_")})

print("== extract ==")
extract = run([str(PYTHON), str(RUNNER), "extract", str(dest), format(EXPECTED, "08X")])
print("extract result:", json.dumps(extract, ensure_ascii=False))
assert extract["detected"] is True, "extract must detect watermark"
print("SMOKE PASS")
