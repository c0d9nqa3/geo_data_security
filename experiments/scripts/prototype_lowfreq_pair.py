from pathlib import Path
import numpy as np, rasterio
from scipy.fft import dctn,idctn
from PIL import Image
p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as ds:x=ds.read(1,window=rasterio.windows.Window(1024,1024,512,512))
V=0xA5A5F00D; bits=[(V>>(31-i))&1 for i in range(32)]
def enc(x,delta):
 n=8;h,w=x.shape;z=x.astype(float).reshape(h//n,n,w//n,n).transpose(0,2,1,3);c=dctn(z,axes=(-2,-1),norm='ortho'); rows,cols=c.shape[:2]
 for r in range(rows):
  for q in range(cols):
   i=(r*cols+q)%32; a,b=c[r,q,2,3],c[r,q,3,2]; mid=(a+b)/2; sign=1 if bits[i] else -1;c[r,q,2,3]=mid+sign*delta/2;c[r,q,3,2]=mid-sign*delta/2
 y=idctn(c,axes=(-2,-1),norm='ortho').transpose(0,2,1,3).reshape(h,w);return np.clip(np.rint(y),0,255).astype(np.uint8)
def dec(x,delta):
 n=8;h,w=x.shape;z=x.astype(float).reshape(h//n,n,w//n,n).transpose(0,2,1,3);c=dctn(z,axes=(-2,-1),norm='ortho');rows,cols=c.shape[:2];votes=np.zeros((32,2),int)
 for r in range(rows):
  for q in range(cols):votes[(r*cols+q)%32,int(c[r,q,2,3]-c[r,q,3,2]>0)]+=1
 v=0
 for i in range(32):v=(v<<1)|int(votes[i,1]>=votes[i,0])
 return v
for d in [1,2,3,4,5,6,8,10,12,16]:
 y=enc(x,d)
 small=np.array(Image.fromarray(y).resize((128,128),Image.Resampling.BILINEAR))
 restored=np.array(Image.fromarray(small).resize((512,512),Image.Resampling.BILINEAR))
 mse=np.mean((x.astype(float)-y.astype(float))**2)
 quality=20*np.log10(255/np.sqrt(mse)) if mse else float('inf')
 print(d,hex(dec(y,d)),hex(dec(restored,d)),round(quality,2),int(np.count_nonzero(x!=y)))
