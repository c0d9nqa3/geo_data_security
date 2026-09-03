from pathlib import Path
import math
import numpy as np
import rasterio
from scipy.fft import dctn,idctn
from PIL import Image

p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as ds:x=ds.read(1,window=rasterio.windows.Window(1024,1024,512,512))
V=0xA5A5F00D; bits=[(V>>(31-i))&1 for i in range(32)]
coords=[(1+(i//8)*2,1+(i%8)*2) for i in range(32)]
def enc(x,step):
 c=dctn(x.astype(np.float32),norm='ortho')
 for bit,(r,q) in zip(bits,coords):
  z=c[r:r+2,q:q+2];u,s,vt=np.linalg.svd(z,full_matrices=False);k=math.floor(abs(float(s[0]))/step)
  if k%2!=bit:k+=1
  s[0]=math.copysign((k+.5)*step,float(s[0]) or 1);c[r:r+2,q:q+2]=(u*s)@vt
 return np.clip(np.rint(idctn(c,norm='ortho')),0,255).astype(np.uint8)
def dec(x,step):
 c=dctn(x.astype(np.float32),norm='ortho');v=0
 for r,q in coords:v=(v<<1)|(math.floor(abs(float(np.linalg.svd(c[r:r+2,q:q+2],full_matrices=False)[1][0]))/step)%2)
 return v
for step in [1,2,3,4,5,6,8,10,12,16,20,24,32,48]:
 y=enc(x,step); small=np.array(Image.fromarray(y).resize((128,128),resample=Image.Resampling.BILINEAR)); up=np.array(Image.fromarray(small).resize((512,512),resample=Image.Resampling.BILINEAR));m=np.mean((x.astype(float)-y.astype(float))**2);pval=20*np.log10(255/np.sqrt(m)) if m else float('inf');print(step,hex(dec(y,step)),hex(dec(up,step)),round(pval,2),int(np.count_nonzero(x!=y)))
