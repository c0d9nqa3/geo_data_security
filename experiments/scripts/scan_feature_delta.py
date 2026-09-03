from pathlib import Path
import cv2,math
import sys
sys.path.insert(0,'server2/pipeline')
import numpy as np,rasterio
from scipy.fft import dctn,idctn
from geo_security.feature_robust_watermark import _features,_bits
p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as d:x=d.read(1)
pts=_features(x,limit=4);print('points',pts);row,col,_=pts[0];half=64;patch=x[row-half:row+half,col-half:col+half];bits=_bits(0xA5A5F00D);coords=[(8+(i%8)*4,12+(i//8)*4) for i in range(32)]
for delta in [2,3,4,5,6,8,10,12,16,20]:
 c=dctn(patch.astype(np.float32),norm='ortho')
 for bit,(r,q) in zip(bits,coords):
  a,b=c[r,q],c[r+1,q+1];mid=(a+b)/2;sg=1 if bit else -1;c[r,q]=mid+sg*delta/2;c[r+1,q+1]=mid-sg*delta/2
 y=np.clip(np.rint(idctn(c,norm='ortho')),0,255).astype(np.uint8);cc=dctn(y.astype(np.float32),norm='ortho');v=0
 for r,q in coords:v=(v<<1)|(int(cc[r,q]-cc[r+1,q+1]>0))
 m=np.mean((patch.astype(float)-y.astype(float))**2);q=20*np.log10(255/np.sqrt(m)) if m else float('inf');print(delta,hex(v),round(q,2),np.count_nonzero(patch!=y))
