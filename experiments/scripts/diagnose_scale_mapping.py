from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
from geo_security.robust_geotiff_watermark import _decode_tile, _grid_mapping, _TILE

base=Path('runtime/robust_matrix_b1/LT51470342011231KHC00_B1')
for name in ['watermarked.tif','resize_50.tif','resize_25.tif']:
 p=base/name
 with rasterio.open(p) as ds:
  print(name,'shape',ds.width,ds.height,'mapping',_grid_mapping(ds),'tags_step',ds.tags().get('GDS_ROBUST_STEP'))
  for sr,sc in [(1024,1024),(2048,2048),(3072,3072)]:
   row,col,scale=_grid_mapping(ds); cr=(sr-row)/scale;cc=(sc-col)/scale
   if cr>=0 and cc>=0 and cr+_TILE/scale<=ds.height and cc+_TILE/scale<=ds.width:
    tile=ds.read(1,window=Window(cc,cr,_TILE/scale,_TILE/scale),out_shape=(1,_TILE,_TILE),resampling=Resampling.bilinear)
    print(' tile',sr,sc,'window',cr,cc,'decode',_decode_tile(tile,float(ds.tags().get('GDS_ROBUST_STEP'))))
