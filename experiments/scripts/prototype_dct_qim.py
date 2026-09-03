import numpy as np
import rasterio
from pathlib import Path
from scipy.fft import dctn, idctn


def bits(v): return np.array([(v>>(31-i))&1 for i in range(32)],dtype=np.uint8)
def run(x,step):
 h,w=x.shape; hh=h//8*8;ww=w//8*8
 b=x[:hh,:ww].astype(np.float32).reshape(hh//8,8,ww//8,8).transpose(0,2,1,3)
 c=dctn(b,axes=(-2,-1),norm='ortho'); ys=np.zeros((32,)); bb=bits(0xA5A5F00D)
 # use blocks in row-major, embed 32 bits repeated across all blocks
 for r in range(c.shape[0]):
  for col in range(c.shape[1]):
   i=(r*c.shape[1]+col)%32; v=c[r,col,2,3]; q=int(np.floor(v/step));
   if q%2 != bb[i]: q += 1
   c[r,col,2,3]=(q+.5)*step
 out=idctn(c,axes=(-2,-1),norm='ortho').transpose(0,2,1,3).reshape(hh,ww); y=x.copy();y[:hh,:ww]=np.clip(np.rint(out),0,255).astype(np.uint8)
 # extract
 b2=y[:hh,:ww].astype(np.float32).reshape(hh//8,8,ww//8,8).transpose(0,2,1,3);c2=dctn(b2,axes=(-2,-1),norm='ortho'); votes=np.zeros((32,2),int)
 for r in range(c2.shape[0]):
  for col in range(c2.shape[1]): votes[(r*c2.shape[1]+col)%32,int(np.floor(c2[r,col,2,3]/step))%2]+=1
 got=sum((int(votes[i,1]>=votes[i,0])<<(31-i)) for i in range(32)); mse=np.mean((x.astype(float)-y.astype(float))**2); p=float('inf') if mse==0 else 20*np.log10(255/np.sqrt(mse));return got,p,np.count_nonzero(x!=y)
for f in [Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')]:
 with rasterio.open(f) as d:x=d.read(1)
 for s in [2,3,4,5,6,8,10]:print(s,run(x,s))
