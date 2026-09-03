from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, maximum_filter, zoom

p=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
with rasterio.open(p) as d:x=d.read(1)
# Feature regions are selected on a 1/16 thumbnail, then mapped to source coordinates.
th=gaussian_filter(x.astype(np.float32),2)[::16,::16]; response=np.abs(gaussian_filter(th,1,order=(2,0)))+np.abs(gaussian_filter(th,1,order=(0,2)))
peaks=(response==maximum_filter(response,size=9))&(response>np.percentile(response,90)); points=np.argwhere(peaks); points=points[np.argsort(response[tuple(points.T)])[::-1]]
selected=[]
for r,c in points:
 y,x0=int(r*16),int(c*16)
 if y+512>x.shape[0] or x0+512>x.shape[1]:continue
 if all(abs(y-a)>256 or abs(x0-b)>256 for a,b in selected):selected.append((y,x0))
 if len(selected)>=8:break
print('selected',selected,'responses',[float(response[r//16,c//16]) for r,c in selected])
