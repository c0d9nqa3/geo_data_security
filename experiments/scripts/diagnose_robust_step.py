from pathlib import Path
import numpy as np,rasterio
import sys
sys.path.insert(0,'server2/pipeline')
from geo_security.robust_geotiff_watermark import _embed_tile,_decode_tile,_step,_TILE
p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as d:x=d.read(1)
tile=x[:_TILE,:_TILE]
for s in [3,8,16,32,64,128,256,512,1024]:
 y=_embed_tile(tile,0xA5A5F00D,s);v,c=_decode_tile(y,s);m=np.mean((tile.astype(float)-y.astype(float))**2);psnr=float('inf') if m==0 else 20*np.log10(255/np.sqrt(m));print(s,hex(v),round(psnr,2),int(np.count_nonzero(tile!=y)),round(c,3))
