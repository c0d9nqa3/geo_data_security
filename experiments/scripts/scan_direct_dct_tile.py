from pathlib import Path
import math
import numpy as np
import rasterio
from scipy.fft import dctn,idctn
p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as ds: x=ds.read(1,window=rasterio.windows.Window(0,0,512,512))
V=0xA5A5F00D; bits=[(V>>(31-i))&1 for i in range(32)]
def run(step):
 c=dctn(x.astype(np.float32),norm='ortho'); coords=[(8+(i//8)*16,8+(i%8)*16) for i in range(32)]
 for i,(r,q) in enumerate(coords):
  z=c[r:r+4,q:q+4];u,s,vt=np.linalg.svd(z,full_matrices=False);b=math.floor(abs(float(s[0]))/step)
  if b%2!=bits[i]:b+=1
  s[0]=math.copysign((b+.5)*step,float(s[0]) or 1);c[r:r+4,q:q+4]=(u*s)@vt
 y=np.clip(np.rint(idctn(c,norm='ortho')),0,255).astype(np.uint8); cc=dctn(y.astype(np.float32),norm='ortho');got=[]
 for r,q in coords:got.append(math.floor(abs(float(np.linalg.svd(cc[r:r+4,q:q+4],full_matrices=False)[1][0]))/step)%2)
 v=0
 for b in got:v=v*2+b
 mse=np.mean((x.astype(float)-y.astype(float))**2); psnr=20*np.log10(255/np.sqrt(mse)) if mse else float('inf');return hex(v),psnr,int(np.count_nonzero(x!=y))
for s in [1,2,3,4,5,6,8,10,12,16,20,24,32]:print(s,run(s))
