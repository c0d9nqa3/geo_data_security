from pathlib import Path
import math
import numpy as np
import pywt
import rasterio
from scipy.fft import dctn, idctn
from rasterio.enums import Resampling
from rasterio.transform import Affine

EXPECTED=0xA5A5F00D

def bits(v): return np.array([(v>>(31-i))&1 for i in range(32)],dtype=np.uint8)
def transform(x):
 h,w=x.shape; hh=h//8*8;ww=w//8*8
 b=x[:hh,:ww].astype(np.float32).reshape(hh//8,8,ww//8,8).transpose(0,2,1,3)
 return b,dctn(b,axes=(-2,-1),norm='ortho'),hh,ww
def inverse(c,shape):
 b=idctn(c,axes=(-2,-1),norm='ortho').transpose(0,2,1,3).reshape(c.shape[0]*8,c.shape[1]*8)
 y=np.zeros(shape,dtype=np.uint8);y[:b.shape[0],:b.shape[1]]=np.clip(np.rint(b),0,255).astype(np.uint8);return y
def embed(x,step=3):
 b,c,hh,ww=transform(x); bb=bits(EXPECTED)
 for r in range(c.shape[0]):
  for q in range(c.shape[1]):
   i=(r*c.shape[1]+q)%32;v=c[r,q,2,3];bucket=math.floor(v/step)
   if bucket%2 != bb[i]:bucket+=1
   c[r,q,2,3]=(bucket+.5)*step
 return inverse(c,x.shape)
def extract(x,step=3):
 _,c,hh,ww=transform(x); best=None
 # Search all possible 8x8 block phases after crop/resampling.
 for pr in range(8):
  for pc in range(8):
   z=x[pr:,pc:]; _,cc,h2,w2=transform(z); votes=np.zeros((32,2),dtype=np.int32)
   for r in range(cc.shape[0]):
    for q in range(cc.shape[1]): votes[(r*cc.shape[1]+q)%32,int(math.floor(cc[r,q,2,3]/step))%2]+=1
   value=sum((int(votes[i,1]>=votes[i,0])<<(31-i)) for i in range(32)); confidence=float(np.sum(np.abs(votes[:,1]-votes[:,0])))/max(1,int(np.sum(votes)))
   candidate=(value==EXPECTED,confidence,value,pr,pc)
   if best is None or candidate[:2]>best[:2]:best=candidate
 return best
p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as ds:x=ds.read(1)
y=embed(x,3); h,w=y.shape;crop=y[(h-h//2)//2:(h-h//2)//2+h//2,(w-w//2)//2:(w-w//2)//2+w//2]
with rasterio.MemoryFile() as mem:
 profile={'driver':'GTiff','width':w,'height':h,'count':1,'dtype':'uint8','transform':Affine.identity()}
 with mem.open(**profile) as ds:ds.write(y,1); small=ds.read(1,out_shape=(1,h//2,w//2),resampling=Resampling.bilinear)
for name,z in [('full',y),('crop',crop),('resize',small)]: print(name,z.shape,extract(z,3))
