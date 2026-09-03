import math
import numpy as np
import pywt
from scipy.fft import dct, idct

from geo_security.geotiff_watermark import _blocks, _bits, psnr


def _carrier(height, width, seed):
    rng = np.random.default_rng(seed)
    raw = rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=(height, width))
    low, details = pywt.dwt2(raw, "haar")
    coeff = dct(dct(details[2], axis=0, norm="ortho"), axis=1, norm="ortho")
    u, singular, vt = np.linalg.svd(coeff, full_matrices=False)
    rank_one = np.outer(u[:, 0], vt[0])
    pattern = idct(idct(rank_one, axis=0, norm="ortho"), axis=1, norm="ortho")
    pattern -= pattern.mean()
    pattern = np.repeat(np.repeat(pattern, 2, axis=0), 2, axis=1)[:height, :width]
    return pattern / (np.sqrt(np.mean(pattern * pattern)) or 1.0)


def embed(x, value, amplitude=1.0):
    out=x.astype(np.float32).copy(); h,w=out.shape; bits=_bits(value); th=h//4; tw=w//8
    for i,bit in enumerate(bits):
        r=(i//8)*th; c=(i%8)*tw; hh=th if i//8<3 else h-r; ww=tw if i%8<7 else w-c
        p=_carrier(hh,ww,1000+i); sign=1 if bit else -1; out[r:r+hh,c:c+ww]+=sign*amplitude*p
    return np.clip(np.rint(out),0,255).astype(np.uint8)

def extract(x, amplitude=1.0):
    h,w=x.shape; th=h//4;tw=w//8;v=0
    for i in range(32):
        r=(i//8)*th;c=(i%8)*tw;hh=th if i//8<3 else h-r;ww=tw if i%8<7 else w-c
        p=_carrier(hh,ww,1000+i); tile=x[r:r+hh,c:c+ww].astype(np.float32); score=float(np.mean((tile-tile.mean())*p));v=(v<<1)|(1 if score>0 else 0)
    return v
for amp in [0.5,1,1.5,2]:
 rng=np.random.default_rng(42);x=rng.integers(0,256,(128,128),dtype=np.uint8);y=embed(x,0xA5A5F00D,amp);print(amp,hex(extract(y,amp)),psnr(x,y),np.count_nonzero(x!=y))
