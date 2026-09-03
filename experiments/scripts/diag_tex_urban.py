"""诊断 urban 纹理 sanity 失败: std、step、每块 sigma1 分布。"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security import texture_watermark as tw  # noqa: E402

WM = 0xA5A5F00D
rng = np.random.default_rng(42)
y, x = np.mgrid[0:512, 0:512]
base = np.zeros((512, 512, 3), dtype=np.uint8)
base[:, :, 0] = ((x // 32) * 40 % 255).astype(np.uint8)
base[:, :, 1] = ((y // 32) * 30 % 255).astype(np.uint8)
base[:, :, 2] = (((x + y) // 64) * 60 % 255).astype(np.uint8)
arr = np.clip(base.astype(np.float64) + rng.normal(0, 6, base.shape), 0, 255).astype(np.uint8)
print("R std:", round(float(np.std(arr[:, :, 0])), 2))

p = Path("runtime/_u.png")
Image.fromarray(arr).save(p)
tw.embed_texture_watermark(p, Path("runtime/_u_wm.png"), WM)
stored = tw._read_step_text(Path("runtime/_u_wm.png"))
print("stored step:", round(stored, 2))
im = np.asarray(Image.open(Path("runtime/_u_wm.png")).convert("RGB"))
chan = tw._transform(im[:, :, 0])
coords = list(tw._coordinates(chan.shape))
want = tw._bits(WM)
got = []
for row, col in coords[:32]:
    block = chan[row:row + 8, col:col + 8]
    _, s, _ = np.linalg.svd(block, full_matrices=False)
    got.append(max(0, int(math.floor(s[0] / stored))) % 2)
ok = sum(a == b for a, b in zip(want, got))
print(f"bits match: {ok}/32")
print("want first16:", want[:16])
print("got  first16:", got[:16])
for i in range(16):
    if want[i] != got[i]:
        block = chan[coords[i][0]:coords[i][0] + 8, coords[i][1]:coords[i][1] + 8]
        _, s, _ = np.linalg.svd(block, full_matrices=False)
        print(f"  bit{i} want={want[i]} got={got[i]} sigma1={s[0]:.1f} bucket={int(s[0]//stored)} step={stored:.1f}")
