from pathlib import Path
import math,time
import numpy as np
import rasterio
from scipy.fft import dctn,idctn
from rasterio.enums import Resampling

P=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
V=0xA5A5F00D; TILE=256; BLOCK=8; STEP=6.0
BITS=np.array([(V>>(31-i))&1 for i in range(32)],dtype=np.uint8)

def dct_tiles(x):
 h,w=x.shape;hh=h//BLOCK*BLOCK;ww=w//BLOCK*BLOCK
 z=x[:hh,:ww].astype(np.float32).reshape(hh//BLOCK,BLOCK,ww//BLOCK,BLOCK).transpose(0,2,1,3)
 return dctn(z,axes=(-2,-1),norm='ortho'),hh,ww

def idct_tiles(c,shape):
 z=idctn(c,axes=(-2,-1),norm='ortho').transpose(0,2,1,3).reshape(c.shape[0]*BLOCK,c.shape[1]*BLOCK)
 y=x0.copy();y[:z.shape[0],:z.shape[1]]=np.clip(np.rint(z),0,255).astype(np.uint8);return y

def embed(x):
 y=x.copy();h,w=x.shape
 for r in range(0,h-TILE+1,TILE):
  for c in range(0,w-TILE+1,TILE):
   tile=x[r:r+TILE,c:c+TILE]; z,_,_=dct_tiles(tile)
   k=0
   for br in range(z.shape[0]):
    for bc in range(z.shape[1]):
     if k>=32:break
     q=math.floor(float(z[br,bc,2,3])/STEP);bit=int(BITS[k]);
     if q%2!=bit:q+=1
     z[br,bc,2,3]=(q+.5)*STEP;k+=1
    if k>=32:break
   y[r:r+TILE,c:c+TILE]=np.clip(np.rint(idctn(z,axes=(-2,-1),norm='ortho').transpose(0,2,1,3).reshape(TILE,TILE)),0,255).astype(np.uint8)
 return y

def decode(tile,step):
 z,_,_=dct_tiles(tile); got=[]; margin=0
 for i in range(32):
  br=i//z.shape[1];bc=i%z.shape[1];v=float(z[br,bc,2,3]);q=math.floor(v/step);got.append(q%2);margin+=abs((v/step)-round(v/step))
 value=0
 for b in got:value=(value<<1)|b
 return value,margin

def extract(x,scale=1.0):
 # Candidate tile sizes correspond to the source 256px tile after resize.
 size=max(BLOCK*8,int(round(TILE*scale))); votes=[];h,w=x.shape
 # A bounded phase grid; each tile is decoded once per phase.
 stride=max(BLOCK, size//8)
 for ro in range(0,min(stride,64),BLOCK):
  for co in range(0,min(stride,64),BLOCK):
   for r in range(ro,h-size+1,size):
    for c in range(co,w-size+1,size):
     value,margin=decode(x[r:r+size,c:c+size],STEP*scale);votes.append((value,margin))
 if not votes:return 0,0,0
 matches=[v for v,m in votes if v==V];return V if len(matches)>len(votes)//2 else max(set(v for v,m in votes),key=lambda v:sum(1 for x,_ in votes if x==v)),len(matches),len(votes)
with rasterio.open(P) as ds:x0=ds.read(1)
t=time.perf_counter();y=embed(x0);print('embed',round(time.perf_counter()-t,2),'changed',int(np.count_nonzero(y!=x0)))
h,w=y.shape;crop=y[(h-h//2)//2:(h-h//2)//2+h//2,(w-w//2)//2:(w-w//2)//2+w//2]
with rasterio.MemoryFile() as m:
 profile={'driver':'GTiff','width':w,'height':h,'count':1,'dtype':'uint8','transform':rasterio.Affine.identity()}
 with m.open(**profile) as ds:ds.write(y,1);small=ds.read(1,out_shape=(1,h//2,w//2),resampling=Resampling.bilinear)
for n,z,s in [('full',y,1),('crop',crop,1),('resize',small,.5)]:
 t=time.perf_counter();print(n,z.shape,extract(z,s),'seconds',round(time.perf_counter()-t,2))
