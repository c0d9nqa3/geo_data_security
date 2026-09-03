from pathlib import Path
import math
import numpy as np
import rasterio
from scipy.fft import dctn,idctn
from rasterio.enums import Resampling
from rasterio.transform import Affine
P=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF'); V=0xA5A5F00D

def bits(v):return np.array([(v>>(31-i))&1 for i in range(32)],dtype=np.uint8)
def blocks(x,n):
 h,w=x.shape;hh=h//n*n;ww=w//n*n;b=x[:hh,:ww].astype(np.float32).reshape(hh//n,n,ww//n,n).transpose(0,2,1,3);return b,dctn(b,axes=(-2,-1),norm='ortho')
def inv(c,n,shape,original):
 z=idctn(c,axes=(-2,-1),norm='ortho').transpose(0,2,1,3).reshape(c.shape[0]*n,c.shape[1]*n)
 out=original.copy();out[:z.shape[0],:z.shape[1]]=np.clip(np.rint(z),0,255).astype(np.uint8);return out
def embed(x,n,step):
 b,c=blocks(x,n); bb=bits(V); rows,cols=c.shape[:2]
 for r in range(rows):
  for q in range(cols):
   i=(r*cols+q)%32;v=c[r,q,2 if n>3 else 1,3 if n>3 else 2]; k=math.floor(v/step)
   if k%2 != bb[i]:k+=1
   if n>3:c[r,q,2,3]=(k+.5)*step
   else:c[r,q,1,2]=(k+.5)*step
 return inv(c,n,x.shape,x)
def extract(x,n,step,phase_r=0,phase_c=0):
 z=x[phase_r:,phase_c:]; b,c=blocks(z,n); rr,cc=c.shape[:2]; votes=np.zeros((32,2),int)
 for r in range(rr):
  for q in range(cc):
   i=(r*cc+q)%32; v=c[r,q,2 if n>3 else 1,3 if n>3 else 2];votes[i,math.floor(v/step)%2]+=1
 val=0
 for i in range(32):val=(val<<1)|int(votes[i,1]>=votes[i,0])
 return val
with rasterio.open(P) as ds:x=ds.read(1)
h,w=x.shape;crop=x[(h-h//2)//2:(h-h//2)//2+h//2,(w-w//2)//2:(w-w//2)//2+w//2]
for n in [8,16,32]:
 for step in [1,1.5,2,2.5,3,4,5,6]:
  y=embed(x,n,step);mse=np.mean((x.astype(float)-y.astype(float))**2);p=float('inf') if mse==0 else 20*np.log10(255/np.sqrt(mse));
  okfull=extract(y,n,step)==V;bestcrop=any(extract(crop,n,step,r,c)==V for r in range(min(n,32)) for c in range(min(n,32)))
  print(n,step,'psnr',round(p,2),'full',okfull,'crop',bestcrop)
PY