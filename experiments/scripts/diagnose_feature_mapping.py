from pathlib import Path
import sys
import cv2
import numpy as np
import rasterio
sys.path.insert(0,'server2/pipeline')
from geo_security.feature_robust_watermark import _DELTA,_decode_patch,_embed_patch,_features,_normalized_patch
p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as d:data=d.read(1)
point=_features(data,1)[0]; patch,fwd=_normalized_patch(data,point); marked=_embed_patch(patch,0xA5A5F00D,_DELTA)
print('point',point.pt,point.size,point.angle,'direct',hex(_decode_patch(marked,_DELTA)[0]))
inv=cv2.invertAffineTransform(fwd); print('fwd',fwd,'inv',inv)
back=cv2.warpAffine(marked,inv,(data.shape[1],data.shape[0]),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
mask=cv2.warpAffine(np.ones_like(marked,dtype=np.uint8),inv,(data.shape[1],data.shape[0]),flags=cv2.INTER_NEAREST)
candidate=data.copy();candidate[mask>0]=back[mask>0]
recovered,_=_normalized_patch(candidate,point);print('roundtrip',hex(_decode_patch(recovered,_DELTA)[0]),'patch_mae',float(np.mean(abs(recovered.astype(float)-marked.astype(float)))),'mask_pixels',int(np.count_nonzero(mask)))
