"""TrustMark 单码字嵌入 512x512 纹理(真实风格照片)的攻击鲁棒性。

纹理尺寸 256~2048 不等; 单码字模式(整图一个码字, TrustMark 训练 resized_crop)
应天然抗 JPEG/缩放/裁剪。此验证决定纹理水印引擎是否切换到 TrustMark。
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TM_VENV = ROOT / "runtime" / "trustmark_venv" / "Scripts" / "python.exe"
sys.path.insert(0, str(TM_VENV.parent))

from trustmark import TrustMark  # noqa: E402

WM = 0xA5A5F00D
OUT = ROOT / "runtime" / "texture_tm_probe"
OUT.mkdir(parents=True, exist_ok=True)

tm = TrustMark(verbose=False, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER,
               loadRemover=False, loadBBoxDetector=False)
payload = format(WM, "032b")

rng = np.random.default_rng(7)
y, x = np.mgrid[0:512, 0:512]


def make(kind):
    base = np.zeros((512, 512, 3), dtype=np.uint8)
    if kind == "gradient":
        base[:, :, 0] = (x * 0.3 + y * 0.2).astype(np.uint8)
        base[:, :, 1] = (255 - y * 0.3).astype(np.uint8)
        base[:, :, 2] = (x * 0.2 + 40).astype(np.uint8)
    elif kind == "urban":
        base[:, :, 0] = ((x // 32) * 40 % 255).astype(np.uint8)
        base[:, :, 1] = ((y // 32) * 30 % 255).astype(np.uint8)
        base[:, :, 2] = (((x + y) // 64) * 60 % 255).astype(np.uint8)
    else:
        base[:, :, 0] = (128 + 60 * np.sin(x / 40) * np.cos(y / 30)).astype(np.uint8)
        base[:, :, 1] = (100 + 40 * np.sin((x + y) / 25)).astype(np.uint8)
        base[:, :, 2] = (90 + 50 * np.cos(y / 20)).astype(np.uint8)
    return np.clip(base.astype(np.float64) + rng.normal(0, 6, base.shape), 0, 255).astype(np.uint8)


def decode(path) -> tuple[bool, int]:
    im = Image.open(path).convert("RGB")
    bits, present, schema = tm.decode(im, MODE="binary")
    if not present or len(bits) < 32:
        return False, -1
    return True, int(bits[:32], 2)


report = []
for kind in ["gradient", "urban", "natural"]:
    arr = make(kind)
    src = OUT / f"{kind}.png"
    marked = OUT / f"{kind}_marked.png"
    Image.fromarray(arr).save(src)
    im = Image.fromarray(arr)
    enc = tm.encode(im, payload, MODE="binary", WM_STRENGTH=1.0)
    enc.save(marked)
    ok0, v0 = decode(marked)
    attacks = {}
    # JPEG q85
    p = OUT / f"{kind}_q85.jpg"
    Image.open(marked).save(p, "JPEG", quality=85)
    attacks["jpeg_q85"] = p
    # resize 50% then restore to 512 (texture atlas rebuild scenario)
    half = Image.open(marked).resize((256, 256), Image.Resampling.BILINEAR)
    p = OUT / f"{kind}_r50.jpg"
    half.save(p, "JPEG", quality=90)
    attacks["resize50_jpeg"] = p
    # crop 70% then restore
    c = Image.open(marked).crop((77, 77, 435, 435)).resize((512, 512), Image.Resampling.BILINEAR)
    p = OUT / f"{kind}_crop.jpg"
    c.save(p, "JPEG", quality=90)
    attacks["crop30_jpeg"] = p
    # noise
    p = OUT / f"{kind}_noise.png"
    n = np.clip(np.asarray(Image.open(marked)).astype(np.int16) + rng.normal(0, 3, (512, 512, 3)), 0, 255).astype(np.uint8)
    Image.fromarray(n).save(p)
    attacks["noise3"] = p

    row = {"texture": kind, "full_ok": ok0, "full_val": hex(v0)}
    for aname, ap in attacks.items():
        ok, v = decode(ap)
        row[aname] = {"ok": ok, "val": hex(v) if v >= 0 else "-"}
    report.append(row)
    print(json.dumps(row), flush=True)

all_ok = all(r["full_ok"] and all(r[k]["ok"] for k in ["jpeg_q85", "resize50_jpeg", "crop30_jpeg", "noise3"]) for r in report)
print(json.dumps({"all_textures_all_attacks_ok": all_ok, "count": len(report)}), flush=True)
