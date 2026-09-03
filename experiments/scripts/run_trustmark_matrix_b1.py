from pathlib import Path
import json
import time

import numpy as np
from PIL import Image, ImageFilter

from trustmark import TrustMark

SOURCE = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")
OUT = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/trustmark_matrix_b1")
OUT.mkdir(parents=True, exist_ok=True)
EXPECTED = 0xA5A5F00D

with __import__('rasterio').open(SOURCE) as ds:
    data = ds.read(1)
    row = (ds.height - 1024) // 2
    col = (ds.width - 1024) // 2
    profile = ds.profile.copy()
    profile.update(width=1024, height=1024, transform=ds.window_transform(__import__('rasterio').windows.Window(col, row, 1024, 1024)))

cover = Image.fromarray(np.repeat(data[:, :, None], 3, axis=2), mode="RGB")
tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)
payload = format(EXPECTED, "032b")
marked = tm.encode(cover, payload, MODE="binary", WM_STRENGTH=1.0)
encoded = np.asarray(marked.convert("RGB"))
base = OUT / "watermarked.tif"
with __import__('rasterio').open(base, "w", **profile) as ds:
    ds.update_tags(GDS_ENGINE="TrustMark-Q", GDS_ECC="BCH_SUPER", GDS_PAYLOAD_BITS=payload)
    ds.write(encoded[:, :, 0].astype(np.uint8), 1)

def decode(image):
    bits, present, schema = tm.decode(image.convert("RGB"), MODE="binary")
    value = int(bits[:32], 2) if present and len(bits) >= 32 else None
    return value, present, schema

def attack_images():
    h, w = encoded.shape[:2]
    yield "full", marked.convert("RGB")
    for name, box in [("crop_random25", (230, 180, 230 + w // 2, 180 + h // 2)), ("crop_random75", (40, 30, 40 + int(w * .75), 30 + int(h * .75)))]:
        yield name, marked.crop(box)
    for scale in [.25, .5, .75, 1.25]:
        yield f"resize_{int(scale*100)}", marked.resize((max(224, int(w*scale)), max(224, int(h*scale))), Image.Resampling.BILINEAR)
    yield "jpeg_q90", Image.open(OUT / "jpeg_q90.jpg") if (OUT / "jpeg_q90.jpg").exists() else marked
    jpeg = OUT / "jpeg_q90.jpg"; marked.save(jpeg, "JPEG", quality=90); yield "jpeg_q90", Image.open(jpeg).convert("RGB")
    arr = np.asarray(marked).astype(np.int16); rng = np.random.default_rng(123); noisy = np.clip(arr + rng.normal(0, 2, arr.shape), 0, 255).astype(np.uint8); yield "noise_sigma2", Image.fromarray(noisy, "RGB")
    yield "gaussian", marked.filter(ImageFilter.GaussianBlur(1.0))
    yield "median", marked.filter(ImageFilter.MedianFilter(3))

rows=[]
for name, image in attack_images():
    started=time.perf_counter()
    try:
        value,present,schema=decode(image); ok=value==EXPECTED; error=None
    except Exception as exc:
        value=None;present=False;schema=-1;ok=False;error=repr(exc)
    rows.append({"scenario":name,"ok":ok,"value":None if value is None else hex(value),"present":present,"schema":schema,"seconds":round(time.perf_counter()-started,3) if error is None else None,"error":error,"size":list(image.size)})
    print(json.dumps(rows[-1],ensure_ascii=False))
(OUT/"report.json").write_text(json.dumps({"expected":hex(EXPECTED),"results":rows},ensure_ascii=False,indent=2),encoding="utf-8")
