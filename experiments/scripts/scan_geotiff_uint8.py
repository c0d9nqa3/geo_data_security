from pathlib import Path
import math
import numpy as np
import pywt
import rasterio
from scipy.fft import dct, idct

from geo_security.geotiff_watermark import _blocks, psnr, _bits

p = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")
with rasterio.open(p) as ds:
    x = ds.read(1).astype(np.float32)
low, details = pywt.dwt2(x, "haar")
diag = dct(dct(details[2], axis=0, norm="ortho"), axis=1, norm="ortho")
bits = _bits(0xA5A5F00D)
for step in [32, 64, 96, 128, 160, 192, 224, 256, 320, 384, 448, 512, 640, 768, 896, 1024]:
    z = diag.copy()
    for index, (row, col) in enumerate(_blocks(z)):
        if index >= 32: break
        block = z[row:row+4, col:col+4]
        u, singular, vt = np.linalg.svd(block, full_matrices=False)
        bucket = max(0, int(math.floor(float(singular[0]) / step)))
        if bucket % 2 != bits[index]: bucket += 1
        singular[0] = (bucket + 0.5) * step
        z[row:row+4, col:col+4] = (u * singular) @ vt
    restored = idct(idct(z, axis=0, norm="ortho"), axis=1, norm="ortho")
    y = pywt.idwt2((low, (details[0], details[1], restored)), "haar")[:x.shape[0], :x.shape[1]]
    q = np.clip(np.rint(y), 0, 255).astype(np.uint8)
    ld, _ = pywt.dwt2(q.astype(np.float32), "haar")
    dq = dct(dct(_[2], axis=0, norm="ortho"), axis=1, norm="ortho")
    got=[]
    for i,(r,c) in enumerate(_blocks(dq)):
        if i>=32: break
        sv=np.linalg.svd(dq[r:r+4,c:c+4],full_matrices=False)[1][0]
        got.append(max(0,int(math.floor(float(sv)/step)))%2)
    value=0
    for bit in got:value=(value<<1)|bit
    print(step, 'changed',int(np.count_nonzero(q!=x)), 'psnr',round(psnr(x,q),2), 'wm',hex(value), 'ok',value==0xA5A5F00D)
