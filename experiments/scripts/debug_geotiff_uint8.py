import numpy as np
import rasterio
import pywt
from scipy.fft import dct, idct

p = r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF"
with rasterio.open(p) as ds:
    x = ds.read(1).astype(np.float32)
low, details = pywt.dwt2(x, "haar")
diag = dct(dct(details[2], axis=0, norm="ortho"), axis=1, norm="ortho")
step = 8.0
z = diag.copy()
for index in range(32):
    row = (index // (diag.shape[1] // 4)) * 4
    col = (index % (diag.shape[1] // 4)) * 4
    block = z[row:row+4, col:col+4]
    u, singular, vt = np.linalg.svd(block, full_matrices=False)
    bucket = max(0, int(np.floor(float(singular[0]) / step)))
    bit = (0xA5A5F00D >> (31-index)) & 1
    if bucket % 2 != bit:
        bucket += 1
    singular[0] = (bucket + 0.5) * step
    z[row:row+4, col:col+4] = (u * singular) @ vt
restored = idct(idct(z, axis=0, norm="ortho"), axis=1, norm="ortho")
out = pywt.idwt2((low, (details[0], details[1], restored)), "haar")[:x.shape[0], :x.shape[1]]
delta = out - x
print("step", step, "float_delta_minmax", float(delta.min()), float(delta.max()), "mean_abs", float(np.mean(np.abs(delta))), "changed_after_round", int(np.count_nonzero(np.rint(out) != x)), "rounded_minmax", int(np.rint(out).min()), int(np.rint(out).max()))
