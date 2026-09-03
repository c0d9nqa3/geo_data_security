"""诊断正式 embed/extract: 二次保存是否改像素 + step 契约。"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security import texture_watermark as tw  # noqa: E402

WM = 0xA5A5F00D
rng = np.random.default_rng(42)
base = np.zeros((512, 512, 3), dtype=np.uint8)
y, x = np.mgrid[0:512, 0:512]
base[:, :, 0] = (x * 0.3 + y * 0.2).astype(np.uint8)
base[:, :, 1] = (255 - y * 0.3).astype(np.uint8)
base[:, :, 2] = (x * 0.2 + 40).astype(np.uint8)
arr = np.clip(base.astype(np.float64) + rng.normal(0, 6, base.shape), 0, 255).astype(np.uint8)

p = Path("runtime/_d2.png")
Image.fromarray(arr).save(p)
tw.embed_texture_watermark(p, Path("runtime/_d2_wm.png"), WM)
stored = tw._read_step_text(Path("runtime/_d2_wm.png"))
print("stored step:", stored)

# pixel diff first vs second save
im1 = np.asarray(Image.open(Path("runtime/_d2_wm.png")).convert("RGB"))
print("extract says:", hex(tw.extract_texture_watermark(Path("runtime/_d2_wm.png"))))

# manually: read image, transform, decode with stored step
chan = tw._transform(im1[:, :, 0])
coords = list(tw._coordinates(chan.shape))
want = tw._bits(WM)
got = []
for row, col in coords[:32]:
    block = chan[row:row + 8, col:col + 8]
    _, s, _ = np.linalg.svd(block, full_matrices=False)
    got.append(max(0, int(np.floor(s[0] / stored))) % 2)
print("manual bits match:", sum(a == b for a, b in zip(want, got)), "/32")
print("want first8:", want[:8])
print("got  first8:", got[:8])
