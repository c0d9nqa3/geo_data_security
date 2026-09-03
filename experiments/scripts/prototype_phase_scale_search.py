from pathlib import Path
import math
import numpy as np
import rasterio
from scipy.fft import dctn,idctn
from rasterio.enums import Resampling
P=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF'); V=0xA5A5F00D

def bits(v): return [(v>>(31-i))&1 for i in range(32)]
def emb(x,B=8,step=3):
 h,w=x.shape; hh=h//B*B;ww=w//B*B; a=x[:hh,:ww].astype(float).reshape(hh//B,B,ww//B,B).transpose(0,2,1,3); c=dctn(a,axes=(-2,-1),norm='ortho'); bb=bits(V)
 for k in range(c.shape[0]*c.shape[1]):
  r,q=divmod(k,c.shape[1]); bucket=math.floor(c[r,q,1,2]/step); bit=bb[k%32]
  if bucket%2!=bit: bucket+=1
  c[r,q,1,2]=(bucket+.5)*step
 y=idctn(c,axes=(-2,-1),norm='ortho').transpose(0,2,1,3).reshape(hh,ww); out=x.copy();out[:hh,:ww]=np.clip(np.rint(y),0,255).astype(np.uint8);return out

def ext(x,B,step=3):
 h,w=x.shape; best=(-1,0,None)
 for oy in range(B):
  for ox in range(B):
   bbnum=(h-oy)//B; wwnum=(w-ox)//B
   if bbnum == 0 or wwnum == 0: continue
   yy=x[oy:oy+bbnum*B,ox:ox+wwnum*B].astype(float); a=yy.reshape(bbnum,B,wwnum,B).transpose(0,2,1,3); c=dctn(a,axes=(-2,-1),norm='ortho'); votes=np.zeros((32,2),int)
   for k in range(bbnum*wwnum):
    r,q=divmod(k,wwnum); votes[k%32,int(math.floor(c[r,q,1,2]/step))%2]+=1
   value=0
   for i in range(32): value=(value<<1)|int(votes[i,1]>=votes[i,0])
   score=sum(max(v) for v in votes)
   if score>best[0]: best=(score,value,(oy,ox,B))
 return best
with rasterio.open(P) as d:x=d.read(1)
y=emb(x);print('full',ext(y,8));h,w=y.shape;crop=y[(h-h//2)//2:(h-h//2)//2+h//2,(w-w//2)//2:(w-w//2)//2+w//2];print('crop',[(B,ext(crop,B)) for B in range(4,17)] )
with rasterio.MemoryFile() as mem:
 with mem.open(driver='GTiff',height=h,width=w,count=1,dtype='uint8') as z:z.write(y,1);small=z.read(1,out_shape=(1,h//2,w//2),resampling=Resampling.bilinear)
print('resize',[(B,ext(small,B)) for B in range(4,17)])
