from pathlib import Path
import math
import numpy as np
import rasterio
from scipy.fft import dctn, idctn
from rasterio.enums import Resampling
from rasterio.windows import Window
from rasterio.transform import Affine

P=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/landsat_full_final/LT51470342011231KHC00_B1_watermarked.tif')
EXPECTED=0xA5A5F00D

def bits(v):return [(v>>(31-i))&1 for i in range(32)]
def process(x,step=3):
 h,w=x.shape;hh=h//8*8;ww=w//8*8
 b=x[:hh,:ww].astype(np.float32).reshape(hh//8,8,ww//8,8).transpose(0,2,1,3)
 c=dctn(b,axes=(-2,-1),norm='ortho'); bb=bits(EXPECTED)
 for r in range(c.shape[0]):
  for q in range(c.shape[1]):
   i=(r*c.shape[1]+q)%32;v=c[r,q,2,3];bucket=math.floor(v/step)
   if bucket%2!=bb[i]: bucket+=1
   c[r,q,2,3]=(bucket+.5)*step
 out=idctn(c,axes=(-2,-1),norm='ortho').transpose(0,2,1,3).reshape(hh,ww);y=x.copy();y[:hh,:ww]=np.clip(np.rint(out),0,255).astype(np.uint8);return y

def extract(x,step=3):
 h,w=x.shape;hh=h//8*8;ww=w//8*8;b=x[:hh,:ww].astype(np.float32).reshape(hh//8,8,ww//8,8).transpose(0,2,1,3);c=dctn(b,axes=(-2,-1),norm='ortho');v=np.zeros((32,2),int)
 for r in range(c.shape[0]):
  for q in range(c.shape[1]):v[(r*c.shape[1]+q)%32,int(math.floor(c[r,q,2,3]/step))%2]+=1
 return sum((int(v[i,1]>=v[i,0])<<(31-i)) for i in range(32))
with rasterio.open(P) as d:x=d.read(1); profile=d.profile.copy();tags=d.tags()
y=process(x);print('full',hex(extract(y)),np.count_nonzero(x!=y))
# crop
h,w=y.shape;cw,ch=w//2,h//2;win=Window((w-cw)//2,(h-ch)//2,cw,ch);crop=y[win.row_off:win.row_off+ch,win.col_off:win.col_off+cw];print('crop',crop.shape,hex(extract(crop)))
# resize via rasterio in memory
with rasterio.MemoryFile() as mem:
 profile.update(width=w,height=h); 
 with mem.open(**profile) as z:z.write(y,1); small=z.read(1,out_shape=(1,h//2,w//2),resampling=Resampling.bilinear)
print('resize',small.shape,hex(extract(small)))
