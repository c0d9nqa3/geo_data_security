from pathlib import Path
import numpy as np
import rasterio
from geo_security.robust_geotiff_watermark import _embed_tile, _decode_tile, _TILE
p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as ds:
 for r in range(0,ds.height-_TILE+1,_TILE):
  for c in range(0,ds.width-_TILE+1,_TILE):
   t=ds.read(1,window=rasterio.windows.Window(c,r,_TILE,_TILE))
   if np.std(t)>=2:
    print('tile',r,c,'minmax',int(t.min()),int(t.max()),'std',float(t.std()))
    for step in [1,2,3,4,6,8,12,16,24,32,48,64]:
     y=_embed_tile(t,0xA5A5F00D,step);v,conf,valid=_decode_tile(y,step);m=np.mean((t.astype(float)-y.astype(float))**2);q=20*np.log10(255/np.sqrt(m)) if m else float('inf');print(step,hex(v),valid,round(q,2),int(np.count_nonzero(t!=y)))
    raise SystemExit
