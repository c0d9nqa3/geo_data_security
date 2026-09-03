from pathlib import Path
import math
import numpy as np
import rasterio
from scipy.fft import dctn,idctn
from rasterio.enums import Resampling
from rasterio.windows import Window
from rasterio.transform import Affine

P=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
V=0xA5A5F00D; B=8

def bits(v):return [(v>>(31-i))&1 for i in range(32)]
def blocks(x):
 h,w=x.shape;hh=h//B*B;ww=w//B*B
 return x[:hh,:ww].astype(np.float32).reshape(hh//B,B,ww//B,B).transpose(0,2,1,3)
def emb(x,step=3):
 a=blocks(x); c=dctn(a,axes=(-2,-1),norm='ortho'); bb=bits(V); n=c.shape[0]*c.shape[1]
 for k in range(n):
  r,q=divmod(k,c.shape[1]); bit=bb[k%32]; z=c[r,q,1,2]; bucket=math.floor(z/step)
  if bucket%2!=bit: bucket+=1
  c[r,q,1,2]=(bucket+.5)*step
 y=idctn(c,axes=(-2,-1),norm='ortho').transpose(0,2,1,3).reshape(c.shape[0]*B,c.shape[1]*B); out=x.copy();out[:y.shape[0],:y.shape[1]]=np.clip(np.rint(y),0,255).astype(np.uint8);return out

def ext(x,step=3):
 a=blocks(x);c=dctn(a,axes=(-2,-1),norm='ortho'); n=c.shape[0]*c.shape[1];best=None
 for phase in range(32):
  votes=np.zeros((32,2),int)
  for k in range(n):
   r,q=divmod(k,c.shape[1]); votes[(k+phase)%32,int(math.floor(c[r,q,1,2]/step))%2]+=1
  v=sum((int(votes[i,1]>=votes[i,0])<<(31-i)) for i in range(32));score=sum(max(z) for z in votes)
  if best is None or score>best[0]:best=(score,v,phase)
 return best
with rasterio.open(P) as d:x=d.read(1); prof=d.profile.copy()
y=emb(x);print('full',ext(y), 'psnr',20*np.log10(255/np.sqrt(np.mean((x.astype(float)-y.astype(float))**2))))
h,w=y.shape;cw,ch=w//2,h//2; crop=y[(h-ch)//2:(h-ch)//2+ch,(w-cw)//2:(w-cw)//2+cw];print('crop',ext(crop))
prof.update(width=w,height=h)
with rasterio.MemoryFile() as mem:
 with mem.open(**prof) as z:z.write(y,1); small=z.read(1,out_shape=(1,h//2,w//2),resampling=Resampling.bilinear)
print('resize',ext(small))
