from __future__ import annotations

import json
from pathlib import Path
import random
import shutil

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.warp import calculate_default_transform, reproject
from scipy.ndimage import gaussian_filter, median_filter
from PIL import Image

from geo_security.robust_geotiff_watermark import (
    embed_geotiff_watermark_robust,
    extract_geotiff_watermark_robust,
)

DATA = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00")
OUT = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/robust_matrix_b1")
EXPECTED = 0xA5A5F00D
OUT.mkdir(parents=True, exist_ok=True)


def write_crop(src, dst, fraction, row_ratio, col_ratio):
    with rasterio.open(src) as ds:
        h, w = ds.height, ds.width
        ch, cw = max(512, int(h * fraction)), max(512, int(w * fraction))
        r = min(h - ch, max(0, int((h - ch) * row_ratio)))
        c = min(w - cw, max(0, int((w - cw) * col_ratio)))
        win = rasterio.windows.Window(c, r, cw, ch)
        profile = ds.profile.copy(); profile.update(width=cw, height=ch, transform=ds.window_transform(win))
        with rasterio.open(dst, 'w', **profile) as out:
            out.update_tags(**ds.tags()); out.write(ds.read(window=win))


def write_resize(src, dst, scale):
    with rasterio.open(src) as ds:
        h, w = max(512, int(ds.height * scale)), max(512, int(ds.width * scale))
        profile = ds.profile.copy(); profile.update(width=w, height=h, transform=ds.transform * Affine.scale(1 / scale, 1 / scale))
        data = ds.read(out_shape=(ds.count, h, w), resampling=Resampling.bilinear)
        with rasterio.open(dst, 'w', **profile) as out:
            out.update_tags(**ds.tags()); out.write(data)


def write_no_custom_tags(src, dst):
    with rasterio.open(src) as ds:
        profile = ds.profile.copy(); tags = {k: v for k, v in ds.tags().items() if not k.startswith('GDS_')}
        with rasterio.open(dst, 'w', **profile) as out:
            out.update_tags(**tags); out.write(ds.read())


def write_jpeg(src, dst, quality):
    with rasterio.open(src) as ds:
        data = ds.read(1)
        Image.fromarray(data).save(dst, format='JPEG', quality=quality)


def write_noise(src, dst, sigma):
    with rasterio.open(src) as ds:
        data = ds.read(1).astype(np.float32)
        rng = np.random.default_rng(12345)
        data = np.clip(np.rint(data + rng.normal(0, sigma, data.shape)), 0, 255).astype(np.uint8)
        profile = ds.profile.copy()
        with rasterio.open(dst, 'w', **profile) as out:
            out.update_tags(**ds.tags()); out.write(data, 1)


def write_filter(src, dst, kind):
    with rasterio.open(src) as ds:
        data = ds.read(1)
        data = median_filter(data, size=3) if kind == 'median' else np.clip(np.rint(gaussian_filter(data.astype(np.float32), 1.0)), 0, 255).astype(np.uint8)
        profile = ds.profile.copy()
        with rasterio.open(dst, 'w', **profile) as out:
            out.update_tags(**ds.tags()); out.write(data, 1)


def write_reproject(src, dst):
    with rasterio.open(src) as ds:
        transform, width, height = calculate_default_transform(ds.crs, 'EPSG:4326', ds.width, ds.height, *ds.bounds)
        profile = ds.profile.copy(); profile.update(crs='EPSG:4326', transform=transform, width=width, height=height)
        data = np.zeros((height, width), dtype=np.uint8)
        reproject(ds.read(1), data, src_transform=ds.transform, src_crs=ds.crs, dst_transform=transform, dst_crs='EPSG:4326', resampling=Resampling.bilinear)
        with rasterio.open(dst, 'w', **profile) as out:
            out.update_tags(**ds.tags()); out.write(data, 1)


def run_band(source: Path, out: Path) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    base = out / 'watermarked.tif'
    embed_geotiff_watermark_robust(source, base, EXPECTED)
    results = []
    for label, fn in [
        ('crop_random_25', lambda p: write_crop(base, p, .25, .17, .73)),
        ('crop_random_75', lambda p: write_crop(base, p, .75, .61, .22)),
        ('crop_center_25', lambda p: write_crop(base, p, .25, .5, .5)),
        ('crop_center_75', lambda p: write_crop(base, p, .75, .5, .5)),
        ('resize_25', lambda p: write_resize(base, p, .25)),
        ('resize_50', lambda p: write_resize(base, p, .50)),
        ('resize_75', lambda p: write_resize(base, p, .75)),
        ('resize_125', lambda p: write_resize(base, p, 1.25)),
        ('delete_custom_tags', lambda p: write_no_custom_tags(base, p)),
        ('jpeg_q90', lambda p: write_jpeg(base, p, 90)),
        ('noise_sigma2', lambda p: write_noise(base, p, 2)),
        ('median_filter3', lambda p: write_filter(base, p, 'median')),
        ('gaussian_filter', lambda p: write_filter(base, p, 'gaussian')),
        ('reproject_4326', lambda p: write_reproject(base, p)),
    ]:
        suffix = '.jpg' if label.startswith('jpeg') else '.tif'
        path = out / f'{label}{suffix}'
        row = {'band': source.stem, 'scenario': label, 'path': str(path)}
        try:
            fn(path)
            value = extract_geotiff_watermark_robust(path)
            row.update({'watermark': hex(value), 'ok': value == EXPECTED})
        except Exception as exc:
            row.update({'watermark': None, 'ok': False, 'error': repr(exc)})
        results.append(row)
    return results

all_results = []
for source in sorted(DATA.glob('*.TIF')):
    all_results.extend(run_band(source, OUT / source.stem))
summary = {}
for scenario in sorted({row['scenario'] for row in all_results}):
    subset = [row for row in all_results if row['scenario'] == scenario]
    summary[scenario] = {'count': len(subset), 'passed': sum(row['ok'] for row in subset), 'rate': sum(row['ok'] for row in subset) / len(subset)}
report = {'expected': hex(EXPECTED), 'results': all_results, 'summary': summary}
(OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
