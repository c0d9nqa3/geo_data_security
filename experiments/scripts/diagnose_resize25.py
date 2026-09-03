import rasterio
from geo_security.robust_geotiff_watermark import _decode_tile, _TILE
p='runtime/robust_matrix_b1/LT51470342011231KHC00_B1/resize_25.tif'
with rasterio.open(p) as ds:
 print(ds.tags(),ds.width,ds.height)
 for s in [3,6,12,24,48,96,192]:
  vals=[]
  for r in range(0,ds.height-512+1,512):
   for c in range(0,ds.width-512+1,512): vals.append(_decode_tile(ds.read(1,window=rasterio.windows.Window(c,r,512,512)),s))
  print(s,vals[:5])
