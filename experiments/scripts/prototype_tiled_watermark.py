from pathlib import Path
import math
import numpy as np
import rasterio
from scipy.fft import dct, idct
from rasterio.enums import Resampling
from rasterio.transform import Affine

P=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
V=0xA5A5F00D; TILE=512; BLOCK=4; STEP=128

def bits(v):return [(v>>(31-i))&1 for i in range(32)]
def tile_transform(x):return dct(dct(x.astype(np.float32),axis=0,norm='ortho'),axis=1,norm='ortho')
def tile_inverse(c):return idct(idct(c,axis=0,norm='ortho'),axis=1,norm='ortho')
def put(tile):
 h,w=tile.shape;c=tile_transform(tile);bb=bits(V)
 for i in range(32):
  r=(i//8)*BLOCK;c0=(i%8)*BLOCK;b=c[r:r+BLOCK,c0:c0+BLOCK];u,s,vt=np.linalg.svd(b,full_matrices=False);q=max(0,int(s[0]//STEP));
  if q%2!=bb[i]:q+=1
  s[0]=(q+.5)*STEP;c[r:r+BLOCK,c0:c0+BLOCK]=(u*s)@vt
 return np.clip(np.rint(tile_inverse(c)),0,255).astype(np.uint8)
def embed(x):
 y=x.copy()
 for r in range(0,x.shape[0]-TILE+1,TILE):
  for c in range(0,x.shape[1]-TILE+1,TILE):y[r:r+TILE,c:c+TILE]=put(x[r:r+TILE,c:c+TILE])
 return y
def read(tile,step=STEP):
 c=tile_transform(tile);v=0
 for i in range(32):
  r=(i//8)*BLOCK;c0=(i%8)*BLOCK;s=np.linalg.svd(c[r:r+BLOCK,c0:c0+BLOCK],full_matrices=False)[1][0];v=(v<<1)|(max(0,int(s//step))%2)
 return v
def extract(x):
 votes=[]
 for size in [TILE,TILE//2,TILE*2]:
  if x.shape[0]<size or x.shape[1]<size:continue
  for ro in range(0,min(size,128),16):
   for co in range(0,min(size,128),16):
    for r in range(ro,x.shape[0]-size+1,size):
     for c in range(co,x.shape[1]-size+1,size):
      z=read(x[r:r+size,c:c+size], STEP*size/TILE); votes.append(read(x[r:r+size,c:c+size],STEP*size/TILE))
 return max(votes,key=lambda v:v==V) if votes else 0
with rasterio.open(P) as d:x=d.read(1)
y=embed(x);h,w=y.shape;crop=y[(h-h//2)//2:(h-h//2)//2+h//2,(w-w//2)//2:(w-w//2)//2+w//2]
with rasterio.MemoryFile() as m:
 profile={'driver':'GTiff','width':w,'height':h,'count':1,'dtype':'uint8','transform':Affine(1,0,0,0,1,0)}
 with m.open(**profile) as d:d.write(y,1);small=d.read(1,out_shape=(1,h//2,w//2),resampling=Resampling.bilinear)
for n,z in [('full',y),('crop',crop),('resize',small)]:print(n,z.shape,hex(extract(z)))
