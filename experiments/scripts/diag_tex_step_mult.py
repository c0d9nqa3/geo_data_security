"""诊断: 提高 step 倍数能否使 SVD 量化载体在噪声纹理上稳定。"""
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

for mult in [1, 2, 4, 8, 16]:
    # monkeypatch embed path by directly writing a variant with scaled step
    orig = Image.fromarray(arr)
    orig.save(f"runtime/_d_m{mult}.png")

    import math

    def embed_scaled(source, destination, watermark, m):
        with Image.open(source) as image:
            rgb = image.convert("RGB")
            array = np.asarray(rgb).copy()
        channel = tw._transform(array[:, :, 0])
        coords = list(tw._coordinates(channel.shape))
        scale = max(float(np.std(array[:, :, 0])), 1.0)
        step = max(scale * 0.5, 4.0) * m
        for bit, (row, col) in zip(tw._bits(watermark), coords):
            block = channel[row:row + 8, col:col + 8]
            u, singular, vt = np.linalg.svd(block, full_matrices=False)
            bucket = max(0, int(math.floor(float(singular[0]) / step)))
            if bucket % 2 != bit:
                bucket += 1
            singular[0] = (bucket + 0.5) * step
            channel[row:row + 8, col:col + 8] = (u * singular) @ vt
        output = array.copy()
        output[:, :, 0] = np.clip(tw._restore(channel), 0, 255).astype(np.uint8)
        Image.fromarray(output).save(destination)

    p = Path(f"runtime/_d_m{mult}.png")
    wm = Path(f"runtime/_d_m{mult}_wm.png")
    embed_scaled(p, wm, WM, mult)
    # extract with same multiplier, read back and count correct bits
    im = np.asarray(Image.open(wm).convert("RGB"))
    chan = tw._transform(im[:, :, 0])
    coords = list(tw._coordinates(chan.shape))
    scale = max(float(np.std(im[:, :, 0])), 1.0)
    step = max(scale * 0.5, 4.0) * mult
    want = tw._bits(WM)
    got_bits = []
    for row, col in coords[:32]:
        block = chan[row:row + 8, col:col + 8]
        _, s, _ = np.linalg.svd(block, full_matrices=False)
        got_bits.append(max(0, int(math.floor(s[0] / step))) % 2)
    ok = sum(a == b for a, b in zip(want, got_bits))
    print(f"mult={mult}: step={round(step,1)}  correct_bits={ok}/32  extracted={hex(sum(b << (31-i) for i,b in enumerate(got_bits)))}")

    # PSNR sanity
    wm_r = np.asarray(Image.open(wm).convert("RGB"))[:, :, 0].astype(np.float64)
    mse = np.mean((arr[:, :, 0].astype(np.float64) - wm_r) ** 2)
    psnr = 20 * np.log10(255.0 / np.sqrt(mse))
    print(f"         psnr(R)={round(psnr,1)}dB")
