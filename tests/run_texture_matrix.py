"""真实纹理(照片)水印鲁棒性矩阵: 嵌入 -> 攻击(缩放/JPEG/噪声) -> 提取。

对照验收指标"格式转换、裁剪、缩放等常规处理后识别率>=90%"(倾斜Mesh纹理)。
发现失败场景即如实记录, 不修数据。
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.texture_watermark import (  # noqa: E402
    embed_texture_watermark,
    extract_texture_watermark,
)

WM = 0xA5A5F00D
OUT = ROOT / "runtime" / "texture_matrix"
OUT.mkdir(parents=True, exist_ok=True)

# synthetic but photo-like textures (smooth gradients + noise + edges, like OSGB photos)
rng = np.random.default_rng(42)
textures = {}
for name, kind in [("photo_a", "gradient"), ("photo_b", "urban"), ("photo_c", "natural")]:
    base = np.zeros((512, 512, 3), dtype=np.uint8)
    y, x = np.mgrid[0:512, 0:512]
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
    noise = rng.normal(0, 6, base.shape)
    base = np.clip(base.astype(np.float64) + noise, 0, 255).astype(np.uint8)
    p = OUT / f"{name}.png"
    Image.fromarray(base).save(p)
    textures[name] = p

ATTACKS = {
    "full": lambda im: im,
    "resize50": lambda im: im.resize((im.width // 2, im.height // 2), Image.Resampling.BILINEAR),
    "resize75": lambda im: im.resize((int(im.width * .75), int(im.height * .75)), Image.Resampling.BILINEAR),
    "jpeg_q85": lambda im: im,
    "noise": lambda im: im,
}


def run_attack(img: Image.Image, name: str) -> Image.Image:
    if name == "full":
        return img.copy()
    if name == "jpeg_q85":
        p = OUT / "_tmp.jpg"
        img.save(p, "JPEG", quality=85)
        return Image.open(p).convert("RGB")
    if name == "noise":
        arr = np.asarray(img)
        n = np.clip(arr.astype(np.int16) + rng.normal(0, 3, arr.shape), 0, 255).astype(np.uint8)
        return Image.fromarray(n)
    return ATTACKS[name](img)


report = []
for tname, src in textures.items():
    marked = OUT / f"{tname}_marked.png"
    embed_texture_watermark(src, marked, WM)
    assert extract_texture_watermark(marked) == WM, "embed sanity failed"
    for attack_name in ATTACKS:
        attacked = run_attack(Image.open(marked), attack_name)
        ap = OUT / f"{tname}_{attack_name}.png"
        attacked.save(ap, format="PNG")
        try:
            got = extract_texture_watermark(ap)
            ok = got == WM
        except Exception as exc:
            ok = False
            got = repr(exc)[:60]
        report.append({"texture": tname, "attack": attack_name, "ok": ok, "got": hex(got) if isinstance(got, int) else got})
        print(json.dumps(report[-1]), flush=True)

passed = sum(1 for r in report if r["ok"])
print(json.dumps({"total": len(report), "passed": passed, "criterion": ">=90% after format/scale attacks", "rate": round(passed / len(report), 3)}), flush=True)
