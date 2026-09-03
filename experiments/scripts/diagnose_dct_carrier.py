from pathlib import Path
import numpy as np
import rasterio
from scipy.fft import dctn
p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as ds: x=ds.read(1,window=rasterio.windows.Window(0,0,512,512)).astype(np.float32)
c=dctn(x,norm='ortho'); print('range',float(x.min()),float(x.max()),'dct range',float(c.min()),float(c.max()))
for pos in [(1,1),(1,2),(2,1),(2,2),(2,3),(3,2),(8,8),(8,9),(16,16)]:
 r,q=pos; b=c[r:r+4,q:q+4]; print(pos,'mean',float(abs(b).mean()),'sv',float(np.linalg.svd(b,full_matrices=False)[1][0]))
# test direct coefficient perturbation
for amp in [0.01,0.05,0.1,0.2,0.5,1,2]:
 z=c.copy(); z[8:12,8:12]+=amp; from scipy.fft import idctn; y=np.clip(np.rint(idctn(z,norm='ortho')),0,255).astype(np.uint8); print('amp',amp,'changed',int(np.count_nonzero(y!=x)),'mae',float(np.mean(abs(y-x))))
