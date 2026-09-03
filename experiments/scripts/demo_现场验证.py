"""现场演示: 真实B1水印文件 -> 攻击 -> 提取, 打印真实结果"""
from pathlib import Path
import sys, json, time

import numpy as np
import rasterio
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

EXPECTED = 0xA5A5F00D
BASE = ROOT / "runtime" / "trustmark_full_tiled" / "B1_full_tiled.tif"
TILE = 1024

with rasterio.open(BASE) as ds:
    arr = ds.read(1)
h, w = arr.shape
rgb = np.repeat(arr[:, :, None], 3, axis=2)
marked = Image.fromarray(rgb, mode="RGB")

tm_det = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)
tm_plain = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)

def decode_one(img, detectfirst):
    bits, present, schema = tm_det.decode(img.convert("RGB"), MODE="binary", DETECTFIRST=detectfirst) if detectfirst else tm_plain.decode(img.convert("RGB"), MODE="binary")
    return present and len(bits) >= 32 and int(bits[:32], 2) == EXPECTED

def verify(name, img, tile_px=TILE, budget=40):
    tw, th = img.size
    win = max(224, int(tile_px))
    t0 = time.perf_counter()
    if tw >= 224 and th >= 224 and decode_one(img, True):
        return {"场景": name, "识别": "通过 ✓", "恢复值": hex(EXPECTED), "耗时_s": round(time.perf_counter()-t0, 1)}
    cands = []
    for gy in range(0, th - win + 1, win):
        for gx in range(0, tw - win + 1, win):
            cands.append((gx, gy))
    step = max(96, win // 8)
    for gy in range(0, th - win + 1, step):
        for gx in range(0, tw - win + 1, step):
            cands.append((gx, gy))
    seen, uniq = set(), []
    for c in cands:
        if c not in seen: seen.add(c); uniq.append(c)
    uniq.sort(key=lambda c: abs(c[0]+win/2-tw/2) + abs(c[1]+win/2-th/2))
    for x, y in uniq[:budget]:
        if decode_one(img.crop((x, y, x+win, y+win)), False):
            return {"场景": name, "识别": "通过 ✓", "恢复值": hex(EXPECTED), "耗时_s": round(time.perf_counter()-t0, 1)}
    return {"场景": name, "识别": "失败 ✗", "耗时_s": round(time.perf_counter()-t0, 1)}

results = []
results.append(verify("原图(无攻击)", marked))
# 随机位置裁剪25%
cw, ch = int(w*.25), int(h*.25)
results.append(verify("随机裁剪25%", marked.crop((1234, 987, 1234+cw, 987+ch))))
# 缩放25% (最难场景)
results.append(verify("缩放25%", marked.resize((int(w*.25), int(h*.25)), Image.Resampling.BILINEAR), int(TILE*.25)))
# JPEG q90
jp = ROOT / "runtime" / "demo_jpeg.jpg"; marked.save(jp, "JPEG", quality=90)
results.append(verify("JPEG压缩q90", Image.open(jp)))
# 中值滤波
results.append(verify("中值滤波3x3", marked.filter(ImageFilter.MedianFilter(3))))
# 重投影回原网格 (4326往返)
from rasterio.warp import calculate_default_transform, reproject, Resampling
with rasterio.open(BASE) as ds:
    t1, w1, h1 = calculate_default_transform(ds.crs, "EPSG:4326", ds.width, ds.height, *ds.bounds)
    a1 = np.empty((h1, w1), dtype=np.uint8)
    reproject(source=ds.read(1), destination=a1, src_transform=ds.transform, src_crs=ds.crs, dst_transform=t1, dst_crs="EPSG:4326", resampling=Resampling.bilinear)
    a2 = np.empty((h, w), dtype=np.uint8)
    reproject(source=a1, destination=a2, src_transform=t1, src_crs="EPSG:4326", dst_transform=ds.transform, dst_crs=ds.crs, resampling=Resampling.bilinear)
results.append(verify("重投影4326往返", Image.fromarray(np.repeat(a2[:, :, None], 3, axis=2), mode="RGB")))

print(json.dumps(results, ensure_ascii=False, indent=2))
ok = sum(1 for r in results if "通过" in r["识别"])
print(f"\n结果: {ok}/{len(results)} 通过")
