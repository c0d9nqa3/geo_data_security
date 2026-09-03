from pathlib import Path
import numpy as np
import rasterio
from geo_security.robust_geotiff_watermark import _embed_tile, _decode_tile

p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as ds: tile=ds.read(1,window=rasterio.windows.Window(0,0,512,512))
for step in [1,2,3,4,5,6,8,10,12,16,20,24,32]:
 out=_embed_tile(tile,0xA5A5F00D,step); val,conf=_decode_tile(out,step); mse=np.mean((tile.astype(float)-out.astype(float))**2); psnr=20*np.log10(255/np.sqrt(mse)) if mse else float('inf')
 print(step,hex(val),round(psnr,2),int(np.count_nonzero(tile!=out)),round(conf,3))
