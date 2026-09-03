from pathlib import Path
import cv2
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.windows import Window
from rasterio.warp import calculate_default_transform, reproject

base=Path('runtime/robust_matrix_b1/LT51470342011231KHC00_B1')
ref=base/'watermarked.tif'

def gray(path):
 with rasterio.open(path) as d:
  a=d.read(1,out_shape=(1,min(1200,d.height),min(1600,d.width)),resampling=Resampling.bilinear)
 return cv2.normalize(a,None,0,255,cv2.NORM_MINMAX).astype(np.uint8)
def match(a,b):
 s=cv2.SIFT_create(nfeatures=1200);ka,da=s.detectAndCompute(gray(a),None);kb,db=s.detectAndCompute(gray(b),None);m=cv2.BFMatcher().knnMatch(da,db,k=2);good=[x for x,y in m if x.distance<.75*y.distance];return len(ka),len(kb),len(good)
for name in ['crop_random_25.tif','crop_random_75.tif','resize_25.tif','resize_50.tif','resize_75.tif','resize_125.tif','reproject_4326.tif']:
 p=base/name
 try:print(name,match(ref,p))
 except Exception as e:print(name,repr(e))
