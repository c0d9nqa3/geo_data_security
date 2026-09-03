"""正式引擎链全矩阵验证: 对真实 B1~B7 用 runner embed -> 生成攻击场景 -> runner extract。

与实验脚本 run_scene_matrix_band.py 等价, 但全程走正式 TrustMarkGeoTIFFEngine
(子进程 runner, 标签记录原空间参考, 重投影自动逆投影)。每场景识别=成功。

用法: python run_engine_matrix_b1b7.py [band...]  默认 1..7
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.trustmark_engine import TrustMarkGeoTIFFEngine  # noqa: E402

EXPECTED = 0xA5A5F00D
SRC_DIR = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00")
OUT = ROOT / "runtime" / "engine_matrix"
OUT.mkdir(parents=True, exist_ok=True)
TILE = 1024

engine = TrustMarkGeoTIFFEngine(timeout=1800)

BANDS = [int(b) for b in sys.argv[1:]] or list(range(1, 8))
summary = {}


def rasterio_read(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(1)


for band in BANDS:
    src = SRC_DIR / f"LT51470342011231KHC00_B{band}.TIF"
    if not src.exists():
        print(json.dumps({"band": band, "error": "missing source"}), flush=True)
        continue
    band_out = OUT / f"B{band}"
    band_out.mkdir(parents=True, exist_ok=True)
    marked = band_out / "marked.tif"
    started = time.perf_counter()
    if not marked.exists():
        engine.embed(src, marked, EXPECTED)
    arr = rasterio_read(marked)
    h, w = arr.shape
    rgb = np.repeat(arr[:, :, None], 3, axis=2)
    img = Image.fromarray(rgb, mode="RGB")
    embed_secs = round(time.perf_counter() - started, 1)

    scenarios = {}

    def add_attack(name, pil_img):
        p = band_out / f"{name}.png"
        pil_img.save(p, format="PNG")
        scenarios[name] = p

    for label, frac, rng in [("crop25_a", .25, (1234, 987)), ("crop25_b", .25, (3111, 2888)), ("crop25_c", .25, (500, 4000)),
                             ("crop75_a", .75, (500, 400)), ("crop75_b", .75, (2500, 3000)), ("crop75_c", .75, (300, 3500))]:
        cw, ch = int(w * frac), int(h * frac)
        x0 = min(rng[0], w - cw); y0 = min(rng[1], h - ch)
        add_attack(label, img.crop((x0, y0, x0 + cw, y0 + ch)))
    for frac in [.25, .5, .75]:
        cw, ch = int(w * frac), int(h * frac)
        x0, y0 = (w - cw) // 2, (h - ch) // 2
        add_attack(f"center{int(frac*100)}", img.crop((x0, y0, x0 + cw, y0 + ch)))
    for scale in [.25, .5, .75, 1.25]:
        add_attack(f"resize{int(scale*100)}", img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR))
    jp = band_out / "jpeg_q90.jpg"
    img.save(jp, "JPEG", quality=90)
    scenarios["jpeg_q90"] = jp
    for k, seed in enumerate([123, 7, 999]):
        rng2 = np.random.default_rng(seed)
        noisy = np.clip(rgb.astype(np.int16) + rng2.normal(0, 2, rgb.shape), 0, 255).astype(np.uint8)
        add_attack(f"noise_b{k}", Image.fromarray(noisy, mode="RGB"))
    add_attack("gaussian", img.filter(ImageFilter.GaussianBlur(1.0)))
    add_attack("median", img.filter(ImageFilter.MedianFilter(3)))
    # reproject 4326 kept as GeoTIFF (tags preserved -> runner warps back automatically)
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    with rasterio.open(marked) as ds:
        t1, w1, h1 = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
        a1 = np.empty((h1, w1), dtype=np.uint8)
        reproject(source=ds.read(1), destination=a1, src_transform=ds.transform, src_crs=ds.crs,
                  dst_transform=t1, dst_crs="EPSG:4326", resampling=Resampling.bilinear)
        tags = ds.tags()
        prof = ds.profile.copy()
        prof.update(crs="EPSG:4326", transform=t1, width=w1, height=h1)
    reproj_tif = band_out / "reproject_4326.tif"
    with rasterio.open(reproj_tif, "w", **prof) as ds:
        ds.update_tags(**tags)
        ds.write(a1, 1)
    scenarios["reproject_4326"] = reproj_tif
    # stripped-tags full image (window scan must still hit without georef tags)
    stripped = band_out / "notags.png"
    img.save(stripped, format="PNG")
    scenarios["notags_full"] = stripped

    results = []
    for name, path in scenarios.items():
        s = time.perf_counter()
        try:
            res = engine.extract(path, EXPECTED)
            ok = bool(res.get("detected"))
            results.append({"scenario": name, "ok": ok, "method": res.get("method"), "attempts": res.get("attempts"), "warped": res.get("warped"), "seconds": round(time.perf_counter() - s, 1)})
        except Exception as exc:
            results.append({"scenario": name, "ok": False, "error": repr(exc), "seconds": round(time.perf_counter() - s, 1)})
        print(json.dumps({"band": band, **results[-1]}, ensure_ascii=False), flush=True)

    passed = sum(1 for r in results if r["ok"])
    summary[band] = {"passed": passed, "total": len(results), "embed_seconds": embed_secs, "fails": [r["scenario"] for r in results if not r["ok"]]}
    (band_out / "report.json").write_text(json.dumps({"expected": hex(EXPECTED), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps({"summary": summary, "total_passed": sum(v["passed"] for v in summary.values()), "total": sum(v["total"] for v in summary.values())}, ensure_ascii=False, indent=2), flush=True)
