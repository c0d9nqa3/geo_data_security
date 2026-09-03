from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import zoom
from rasterio.enums import Resampling

P=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF'); V=0xA5A5F00D; AMP=1.0

def bits(v):return np.array([(v>>(31-i))&1 for i in range(32)])*2-1
def pat(shape,seed):
 rng=np.random.default_rng(seed); p=rng.choice([-1.,1.],size=shape); p=p-p.mean();return p/(np.sqrt(np.mean(p*p)) or 1)
def embed(x):
 y=x.astype(np.float32).copy(); b=bits(V)
 for i,s in enumerate(b): y+=s*AMP*pat(x.shape,100+i)
 return np.clip(np.rint(y),0,255).astype(np.uint8)
def extract(x):
 scores=[]
 for i in range(32):scores.append(float(np.mean((x.astype(np.float32)-x.mean())*pat(x.shape,100+i))))
 return sum((int(s>0)<<(31-i)) for i,s in enumerate(scores)), min(abs(s) for s in scores), np.mean(np.array(scores)*bits(V))
with rasterio.open(P) as d:x=d.read(1)
y=embed(x); h,w=y.shape; crop=y[(h-h//2)//2:(h-h//2)//2+h//2,(w-w//2)//2:(w-w//2)//2+w//2]
with rasterio.MemoryFile() as m:
 pr={'driver':'GTiff','width':w,'height':h,'count':1,'dtype':'uint8','transform':rasterio.Affine.identity()}
 with m.open(**pr) as d:d.write(y,1);small=d.read(1,out_shape=(1,h//2,w//2),resampling=Resampling.bilinear)
for n,z in [('full',y),('crop',crop),('resize',small)]:print(n,z.shape,hex(extract(z)[0]),extract(z)[1:])
