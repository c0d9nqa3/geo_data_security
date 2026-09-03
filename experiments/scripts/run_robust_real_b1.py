from pathlib import Path
import json
import time
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window
from rasterio.transform import Affine
from geo_security.robust_geotiff_watermark import embed_geotiff_watermark_robust, extract_geotiff_watermark_robust

SOURCE = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")
OUT = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/robust_real_b1")
OUT.mkdir(parents=True, exist_ok=True)
WM = 0xA5A5F00D
watermarked = OUT / "watermarked.tif"
psnr = embed_geotiff_watermark_robust(SOURCE, watermarked, WM)
results = [{"scenario": "full", "watermark": hex(extract_geotiff_watermark_robust(watermarked)), "psnr": psnr}]
with rasterio.open(watermarked) as ds:
    h, w = ds.height, ds.width
    crop_h, crop_w = h // 2, w // 2
    r0, c0 = (h - crop_h) // 2, (w - crop_w) // 2
    crop_window = Window(c0, r0, crop_w, crop_h)
    crop = OUT / "crop.tif"
    cp = ds.profile.copy(); cp.update(width=crop_w, height=crop_h, transform=ds.window_transform(crop_window))
    with rasterio.open(crop, "w", **cp) as out:
        out.update_tags(**ds.tags()); out.write(ds.read(window=crop_window))
    resize = OUT / "resize.tif"
    rp = ds.profile.copy(); rp.update(width=w // 2, height=h // 2, transform=ds.transform * Affine.scale(2, 2))
    data = ds.read(out_shape=(ds.count, h // 2, w // 2), resampling=Resampling.bilinear)
    with rasterio.open(resize, "w", **rp) as out:
        out.update_tags(**ds.tags()); out.write(data)
for name, path in [("crop_50", crop), ("resize_50", resize)]:
    started = time.perf_counter()
    try: value = extract_geotiff_watermark_robust(path); error = None
    except Exception as exc: value = None; error = repr(exc)
    results.append({"scenario": name, "watermark": None if value is None else hex(value), "ok": value == WM, "seconds": round(time.perf_counter()-started,3), "error": error})
print(json.dumps(results, ensure_ascii=False, indent=2))
