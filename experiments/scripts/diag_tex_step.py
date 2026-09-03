"""诊断 texture watermark: step 往返、量化桶一致、逐位比对。"""
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
noise = rng.normal(0, 6, base.shape)
arr = np.clip(base.astype(np.float64) + noise, 0, 255).astype(np.uint8)

p = Path("runtime/_diag_tex.png")
Image.fromarray(arr).save(p)
tw.embed_texture_watermark(p, Path("runtime/_diag_tex_wm.png"), WM)

stored = tw._read_step_text(Path("runtime/_diag_tex_wm.png"))
print("stored step:", stored)
got = tw.extract_texture_watermark(Path("runtime/_diag_tex_wm.png"))
print("got:", hex(got), "want:", hex(WM))

# reconstruct: read saved wm file as raw, then re-derive step and extract
im = np.asarray(Image.open("runtime/_diag_tex_wm.png").convert("RGB"))
chan = tw._transform(im[:, :, 0])
coords = list(tw._coordinates(chan.shape))
scale = max(float(np.std(im[:, :, 0])), 1.0)
step_rederived = max(scale * 0.5, 4.0)
print("original-step-at-embed was max(orig_std*0.5,4); orig std:", round(float(np.std(arr[:, :, 0])), 2), "wm std:", round(float(np.std(im[:, :, 0])), 2))
print("rederived step:", step_rederived)

# bit dump under stored vs rederived step
want_bits = tw._bits(WM)
b_stored, b_re = [], []
for row, col in coords[:32]:
    block = chan[row:row + 8, col:col + 8]
    _, s, _ = np.linalg.svd(block, full_matrices=False)
    b_stored.append(max(0, int(np.floor(s[0] / stored))) % 2)
    b_re.append(max(0, int(np.floor(s[0] / step_rederived))) % 2)
print("bits match stored:", sum(a == b for a, b in zip(want_bits, b_stored)), "/32")
print("bits match rederived:", sum(a == b for a, b in zip(want_bits, b_re)), "/32")
print("first 8 want:", want_bits[:8])
print("first 8 stored:", b_stored[:8])
