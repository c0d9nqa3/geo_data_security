import math
import numpy as np
import pywt
from scipy.fft import dct,idct
from geo_security.geotiff_watermark import _blocks,_bits,psnr
rng=np.random.default_rng(42); x=rng.integers(0,256,(128,128),dtype=np.uint8).astype(np.float32)
low,det=pywt.dwt2(x,'haar'); diag=dct(dct(det[2],axis=0,norm='ortho'),axis=1,norm='ortho'); bits=_bits(0xA5A5F00D)
for step in [64,96,128,160,192,224,256,320,384,448,512,640,768,896,1024]:
 z=diag.copy()
 for i,(r,c) in enumerate(_blocks(z)):
  if i>=32:break
  b=z[r:r+4,c:c+4];u,s,vt=np.linalg.svd(b,full_matrices=False); bucket=max(0,int(s[0]//step));
  if bucket%2!=bits[i]:bucket+=1
  s[0]=(bucket+.5)*step;z[r:r+4,c:c+4]=(u*s)@vt
 restored=idct(idct(z,axis=0,norm='ortho'),axis=1,norm='ortho'); y=pywt.idwt2((low,(det[0],det[1],restored)),'haar')[:128,:128]; q=np.clip(np.rint(y),0,255).astype(np.uint8)
 _,dd=pywt.dwt2(q.astype(np.float32),'haar'); dq=dct(dct(dd[2],axis=0,norm='ortho'),axis=1,norm='ortho'); got=[]
 for i,(r,c) in enumerate(_blocks(dq)):
  if i>=32:break
  got.append(max(0,int(np.linalg.svd(dq[r:r+4,c:c+4],full_matrices=False)[1][0]//step))%2)
 v=0
 for bit in got:v=(v<<1)|bit
 print(step,'psnr',round(psnr(x,q),2),'changed',np.count_nonzero(q!=x),'wm',hex(v),v==0xA5A5F00D)
