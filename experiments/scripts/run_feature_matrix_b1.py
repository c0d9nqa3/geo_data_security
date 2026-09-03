from pathlib import Path
import json
import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.windows import Window
from rasterio.warp import calculate_default_transform, reproject

import sys
sys.path.insert(0, 'server2/pipeline')
from geo_security.feature_robust_watermark import embed_feature_watermark, extract_feature_watermark

SOURCE=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF')
OUT=Path(r'C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/feature_matrix_b1');OUT.mkdir(parents=True,exist_ok=True)
V=0xA5A5F00D;base=OUT/'watermarked.tif';psnr=embed_feature_watermark(SOURCE,base,V);rows=[{'scenario':'full','ok':extract_feature_watermark(base)==V,'psnr':psnr}]
def crop(path,f,rr,cc):
 with rasterio.open(base) as d:
  h,w=d.height,d.width;ch,cw=int(h*f),int(w*f);r=int((h-ch)*rr);c=int((w-cw)*cc);win=Window(c,r,cw,ch);pr=d.profile.copy();pr.update(width=cw,height=ch,transform=d.window_transform(win));
  with rasterio.open(path,'w',**pr) as o:o.update_tags(**d.tags());o.write(d.read(window=win))
def resize(path,f):
 with rasterio.open(base) as d:
  h,w=int(d.height*f),int(d.width*f);pr=d.profile.copy();pr.update(width=w,height=h,transform=d.transform*Affine.scale(1/f,1/f));z=d.read(out_shape=(1,h,w),resampling=Resampling.bilinear)
  with rasterio.open(path,'w',**pr) as o:o.update_tags(**d.tags());o.write(z)
def no_tags(path):
 with rasterio.open(base) as d:
  pr=d.profile.copy(); tags={k:v for k,v in d.tags().items() if not k.startswith('GDS_')}
  with rasterio.open(path,'w',**pr) as o:o.update_tags(**tags);o.write(d.read())
def jpeg(path):
 with rasterio.open(base) as d:Image.fromarray(d.read(1)).save(path,'JPEG',quality=90)
def noise(path):
 with rasterio.open(base) as d:
  z=np.clip(np.rint(d.read(1).astype(float)+np.random.default_rng(9).normal(0,2,d.shape)),0,255).astype('uint8');pr=d.profile.copy()
  with rasterio.open(path,'w',**pr) as o:o.update_tags(**d.tags());o.write(z,1)
def filt(path):
 from scipy.ndimage import gaussian_filter
 with rasterio.open(base) as d:
  z=np.clip(np.rint(gaussian_filter(d.read(1).astype(float),1)),0,255).astype('uint8');pr=d.profile.copy()
  with rasterio.open(path,'w',**pr) as o:o.update_tags(**d.tags());o.write(z,1)
def reproj(path):
 with rasterio.open(base) as d:
  tr,w,h=calculate_default_transform(d.crs,'EPSG:4326',d.width,d.height,*d.bounds);pr=d.profile.copy();pr.update(crs='EPSG:4326',transform=tr,width=w,height=h);z=np.zeros((h,w),dtype='uint8');reproject(d.read(1),z,src_transform=d.transform,src_crs=d.crs,dst_transform=tr,dst_crs='EPSG:4326',resampling=Resampling.bilinear)
  with rasterio.open(path,'w',**pr) as o:o.update_tags(**d.tags());o.write(z,1)
writers=[('crop_random25',lambda p:crop(p,.25,.17,.73)),('crop_random75',lambda p:crop(p,.75,.61,.22)),('resize25',lambda p:resize(p,.25)),('resize50',lambda p:resize(p,.5)),('resize75',lambda p:resize(p,.75)),('resize125',lambda p:resize(p,1.25)),('delete_tags',no_tags),('jpeg90',jpeg),('noise2',noise),('gaussian',filt),('reproject4326',reproj)]
for n,fn in writers:
 p=OUT/(n+('.jpg' if n.startswith('jpeg') else '.tif'));row={'scenario':n,'path':str(p)}
 try:fn(p);row.update({'watermark':hex(extract_feature_watermark(p)),'ok':extract_feature_watermark(p)==V})
 except Exception as e:row.update({'ok':False,'error':repr(e)})
 rows.append(row);print(json.dumps(row,ensure_ascii=False))
(OUT/'report.json').write_text(json.dumps({'expected':hex(V),'results':rows},ensure_ascii=False,indent=2),encoding='utf-8')
