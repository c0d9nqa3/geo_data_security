from pathlib import Path
import sys
import time

import numpy as np
import rasterio
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

SOURCE = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")
OUT = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/geo_data_security/runtime/trustmark_b1")
OUT.mkdir(parents=True, exist_ok=True)

with rasterio.open(SOURCE) as ds:
    h, w = ds.height, ds.width
    row = (h - 1024) // 2
    col = (w - 1024) // 2
    data = ds.read(1, window=rasterio.windows.Window(col, row, 1024, 1024))

rgb = np.repeat(data[:, :, None], 3, axis=2)
cover = Image.fromarray(rgb, mode="RGB")
started = time.perf_counter()
tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False)
binary_payload = format(0xA5A5F00D, "032b")
encoded = tm.encode(cover, binary_payload, MODE="binary", WM_STRENGTH=1.0)
secret, present, schema = tm.decode(encoded.convert("RGB"), MODE="binary")
secret_bits = secret if isinstance(secret, str) else ""
recovered = int(secret_bits, 2) if present and len(secret_bits) >= 32 else None
output = OUT / "B1_center_1024_trustmark.tif"
with rasterio.open(SOURCE) as source:
    profile = source.profile.copy()
    profile.update(width=1024, height=1024, count=1, transform=source.window_transform(rasterio.windows.Window(col, row, 1024, 1024)))
with rasterio.open(output, "w", **profile) as ds:
    ds.update_tags(GDS_ENGINE="TrustMark-Q-BCH_SUPER", GDS_TRUSTMARK_PAYLOAD="A5A5F00D")
    ds.write(np.asarray(encoded.convert("RGB"))[:, :, 0].astype(np.uint8), 1)
original = np.asarray(cover.convert("L"), dtype=np.float64)
marked = np.asarray(encoded.convert("L"), dtype=np.float64)
mse = float(np.mean((original - marked) ** 2))
psnr = float("inf") if mse == 0 else 20 * np.log10(255 / np.sqrt(mse))
print({"output": str(output), "seconds": round(time.perf_counter()-started,3), "secret": secret, "recovered": None if recovered is None else hex(recovered), "present": present, "schema": schema, "psnr_db": psnr, "crs": str(profile.get("crs")), "shape": [1024,1024]})
