from pathlib import Path
import sys
import cv2
import numpy as np
import rasterio
from scipy.fft import dctn,idctn
sys.path.insert(0,'server2/pipeline')
from geo_security.feature_robust_watermark import _features,_bits
p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as d:data=d.read(1)
point=_features(data,1)[0]; patch,_=__import__('geo_security.feature_robust_watermark',fromlist=['_normalized_patch'])._normalized_patch(data,point);bits=_bits(0xA5A5F00D)
coords=[(10+(i%8)*5,12+(i//8)*5) for i in range(32)]
for delta in [8,12,16,20,24,32,40,48,64,80,96]:
 c=dctn(patch.astype(np.float32),norm='ortho')
 for i,(r,q) in enumerate(coords):
  a,b=float(c[r,q]),float(c[r+1,q+1]);mid=(a+b)/2;sg=1 if bits[i] else -1;c[r,q]=mid+sg*delta/2;c[r+1,q+1]=mid-sg*delta/2
 y=np.clip(np.rint(idctn(c,norm='ortho')),0,255).astype(np.uint8);cc=dctn(y.astype(np.float32),norm='ortho');v=0
 for r,q in coords:v=(v<<1)|int(cc[r,q]-cc[r+1,q+1]>0)
 mse=np.mean((patch.astype(float)-y.astype(float))**2);qv=20*np.log10(255/np.sqrt(mse)) if mse else float('inf');print(delta,hex(v),round(qv,2),int(np.count_nonzero(patch!=y)))
