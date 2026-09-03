from pathlib import Path
import math
import numpy as np
import rasterio
from scipy.fft import dct

P=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/landsat_full_final/LT51470342011231KHC00_B1_watermarked.tif')
V=0xA5A5F00D; TILE=256; BLOCK=8; STEP=3
BITS=[(V>>(31-i))&1 for i in range(32)]
def decode(tile,step):
 h,w=tile.shape; h=h//BLOCK*BLOCK;w=w//BLOCK*BLOCK; b=tile[:h,:w].astype(np.float32).reshape(h//BLOCK,BLOCK,w//BLOCK,BLOCK).transpose(0,2,1,3);c=dct(dct(b,axis=-2,norm='ortho'),axis=-1,norm='ortho'); val=0
 for i in range(32):
  br=i//c.shape[1];bc=i%c.shape[1];val=(val<<1)|(math.floor(float(c[br,bc,2,3])/step)%2)
 return val
with rasterio.open(P) as ds:y=ds.read(1)
h,w=y.shape; r0=(h-h//2)//2;c0=(w-w//2)//2;crop=y[r0:r0+h//2,c0:c0+w//2]
print('crop_origin',r0,c0,'mod',r0%TILE,c0%TILE)
for rr,cc in [(0,0),(TILE-r0%TILE,TILE-c0%TILE),(TILE-r0%TILE,0),(0,TILE-c0%TILE)]:
 print('phase',rr,cc,'values', [hex(decode(crop[rr+i*TILE:rr+(i+1)*TILE,cc+j*TILE:cc+(j+1)*TILE],STEP)) for i,j in [(0,0),(0,1),(1,0),(1,1),(5,5)]])
