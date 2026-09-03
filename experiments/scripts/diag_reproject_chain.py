"""诊断 reproject -> extract 全链路。"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "runtime" / "trustmark_venv" / "Scripts" / "python.exe"
RUNNER = ROOT / "server2" / "pipeline" / "geo_security" / "trustmark_geotiff_runner.py"
EXPECTED = 0x1357BDFF
tmp = ROOT / "runtime" / "diag_reproj"
tmp.mkdir(parents=True, exist_ok=True)

src = tmp / "src.tif"
marked = tmp / "marked.tif"
reproj = tmp / "reproj.tif"

rng = np.random.default_rng(21)
values = rng.integers(0, 256, (1024, 1024), dtype=np.uint8)
profile = {"driver": "GTiff", "height": 1024, "width": 1024, "count": 1, "dtype": "uint8", "crs": "EPSG:32644", "transform": from_origin(500000, 4000000, 30, 30)}
with rasterio.open(src, "w", **profile) as ds:
    ds.write(values, 1)

def run(args):
    p = subprocess.run([str(PYTHON), str(RUNNER), *args], capture_output=True, text=True, encoding="utf-8", timeout=1800)
    print("rc:", p.returncode, "stderr tail:", (p.stderr or "").strip()[-300:])
    if p.stdout.strip():
        print("stdout:", p.stdout.strip()[-400:])
    p.check_returncode()
    return json.loads(p.stdout.strip().splitlines()[-1])

print("== embed ==")
print(run(["embed", str(src), str(marked), format(EXPECTED, "08X")]))

with rasterio.open(marked) as ds:
    print("marked tags:", {k: v for k, v in ds.tags().items() if k.startswith("GDS_TM")})

print("== reproject to 4326 (keep tags) ==")
with rasterio.open(marked) as ds:
    transform, width, height = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
    prof = ds.profile.copy()
    prof.update(crs="EPSG:4326", transform=transform, width=width, height=height)
    tags = ds.tags()
    arr = np.empty((height, width), dtype=np.uint8)
    reproject(source=rasterio.band(ds, 1), destination=arr, src_transform=ds.transform, src_crs=ds.crs,
              dst_transform=transform, dst_crs="EPSG:4326", resampling=Resampling.bilinear)
with rasterio.open(reproj, "w", **prof) as ds:
    ds.update_tags(**tags)
    ds.write(arr, 1)
with rasterio.open(reproj) as ds:
    print("reproj crs:", ds.crs, "size:", (ds.width, ds.height), "tags:", {k: v for k, v in ds.tags().items() if k.startswith("GDS_TM")})

print("== extract on reprojected ==")
res = run(["extract", str(reproj), format(EXPECTED, "08X")])
print("extract:", json.dumps(res))
