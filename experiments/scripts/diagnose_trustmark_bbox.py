from pathlib import Path
import sys

import numpy as np
import rasterio
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

BASE = ROOT / "runtime" / "trustmark_matrix_b1" / "watermarked.tif"

with rasterio.open(BASE) as ds:
    rgb = np.repeat(ds.read(1)[:, :, None], 3, axis=2)
marked = Image.fromarray(rgb, mode="RGB")
w, h = marked.size
print({"source_size": [w, h]}, flush=True)

variants = {"full": marked}
for name, box in [
    ("crop_center25", (int(w * .375), int(h * .375), int(w * .625), int(h * .625))),
    ("crop_center75", (int(w * .125), int(h * .125), int(w * .875), int(h * .875))),
    ("crop_random25", (int(w * .17), int(h * .31), int(w * .42), int(h * .56))),
    ("crop_random75", (int(w * .05), int(h * .07), int(w * .80), int(h * .82))),
]:
    variants[name] = marked.crop(box)

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)
for name, image in variants.items():
    try:
        boxes = tm.localize(image, return_all=True)
        box_str = "None" if boxes is None else [[round(v, 3) for v in b] for b in boxes][:4]
        n = 0 if boxes is None else len(boxes)
        print({"scenario": name, "size": list(image.size), "n_boxes": n, "boxes": box_str}, flush=True)
        if boxes:
            for bbox in boxes:
                x1, y1, x2, y2 = [int(v * dim) for v, dim in zip(bbox, image.size * 2)]
                x1, y1 = int(bbox[0] * image.size[0]), int(bbox[1] * image.size[1])
                x2, y2 = int(bbox[2] * image.size[0]), int(bbox[3] * image.size[1])
                sub = image.crop((x1, y1, x2, y2))
                bits, present, schema = tm.decode(sub.convert("RGB"), MODE="binary")
                value = int(bits[:32], 2) if present and len(bits) >= 32 else None
                print({"   box_decode": {"present": present, "value": None if value is None else hex(value), "schema": schema}}, flush=True)
    except Exception as exc:
        print({"scenario": name, "error": repr(exc)}, flush=True)
