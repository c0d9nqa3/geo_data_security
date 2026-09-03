"""TrustMark 瓦片 GeoTIFF 水印 runner（由独立 trustmark venv 的 python 执行）。

主项目环境 numpy>=2 与 torch 2.1.2 冲突，因此本 runner 必须用
runtime/trustmark_venv/Scripts/python.exe 执行（该环境 numpy<2 + torch 2.1.2+cpu +
trustmark 0.9.0 editable + rasterio + pyproj）。

用法:
    trustmark_geotiff_runner.py embed <source.tif> <dest.tif> <hex_watermark>
    trustmark_geotiff_runner.py extract <source.tif> <expected_hex>   # 检测并输出是否命中

约定:
- GeoTIFF 单波段灰度; 复制为 RGB 供 TrustMark; 嵌入后取 R 通道写回原 profile。
- 1024x1024 瓦片网格, 每瓦片独立嵌入同一 40bit BCH_SUPER 码字(32bit 业务位)。
- 保留原 dtype/CRS/transform/tags。
- stdout 输出单行 JSON; 失败非零退出并输出错误到 stderr。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from trustmark import TrustMark

EXPECTED_HEX_TAG = "GDS_TM_PAYLOAD"
TILE = 1024
_ENCODING = TrustMark.Encoding.BCH_SUPER


def _make_tm(load_bbox: bool = False) -> TrustMark:
    return TrustMark(
        verbose=False,
        model_type="Q",
        encoding_type=_ENCODING,
        loadRemover=False,
        loadBBoxDetector=load_bbox,
    )


def _payload_bits(watermark: int) -> str:
    return format(watermark, "032b")


def embed(source: Path, destination: Path, watermark: int) -> dict:
    source, destination = Path(source), Path(destination)
    with rasterio.open(source) as ds:
        data = ds.read(1)
        profile = ds.profile.copy()
        tags = ds.tags()
    if data.dtype != np.uint8:
        raise ValueError(f"GeoTIFF must be uint8 for TrustMark tiled embed, got {data.dtype}")
    h, w = data.shape
    if h < TILE or w < TILE:
        raise ValueError(f"GeoTIFF too small for TrustMark tiling: {w}x{h}, need >= {TILE}x{TILE}")
    tm = _make_tm()
    payload = _payload_bits(watermark)
    rgb = np.repeat(data[:, :, None], 3, axis=2)
    marked = np.empty_like(rgb)
    tiles = 0
    for ty in range(0, h, TILE):
        for tx in range(0, w, TILE):
            y2, x2 = min(ty + TILE, h), min(tx + TILE, w)
            tile = Image.fromarray(rgb[ty:y2, tx:x2], mode="RGB")
            encoded = tm.encode(tile, payload, MODE="binary", WM_STRENGTH=1.0)
            marked[ty:y2, tx:x2] = np.asarray(encoded)
            tiles += 1
    mse = float(np.mean((rgb.astype(np.float64) - marked.astype(np.float64)) ** 2))
    psnr = float("inf") if mse == 0 else 20 * np.log10(255.0 / np.sqrt(mse))
    with rasterio.open(destination, "w", **profile) as ds:
        ds.update_tags(**tags)
        ds.update_tags(GDS_TM_ENGINE="TrustMark-Q-TILED1024", GDS_TM_ECC="BCH_SUPER", EXPECTED_HEX_TAG=format(watermark, "08X"))
        ds.write(marked[:, :, 0].astype(np.uint8), 1)
    return {"tiles": tiles, "psnr_db": round(psnr, 3), "dtype": str(np.uint8), "width": w, "height": h}


def _decode_ok(tm: TrustMark, image: Image.Image, expected: int) -> bool:
    bits, present, schema = tm.decode(image.convert("RGB"), MODE="binary")
    return bool(present) and len(bits) >= 32 and int(bits[:32], 2) == expected


def extract(source: Path, expected_hex: str, max_windows: int = 400) -> dict:
    source = Path(source)
    expected = int(expected_hex, 16)
    with rasterio.open(source) as ds:
        data = ds.read(1)
        w, h = data.shape[1], data.shape[0]
    rgb = np.repeat(data[:, :, None], 3, axis=2)
    image = Image.fromarray(rgb, mode="RGB")
    tm_det = _make_tm(load_bbox=True)
    tm_plain = _make_tm()
    # prong 1: bbox detect over whole image
    try:
        bits, present, schema = tm_det.decode(image.convert("RGB"), MODE="binary", DETECTFIRST=True)
        if present and len(bits) >= 32 and int(bits[:32], 2) == expected:
            return {"detected": True, "method": "bbox_detect", "expected": expected_hex}
    except Exception:
        pass
    # prong 2: multi-scale windows. Buckets ordered by likelihood: original 1024 tile
    # first (full/crop/JPEG/noise keep tile size), then shrinking (resize-down), then
    # growing (resize-up).
    # Within a bucket, grid-aligned windows (every `win` px) are tried FIRST in raster
    # order: a crop shifts the tile phase by only a few px, so an aligned window sits
    # within decoder tolerance even when the bbox detector fails. Fine sliding windows
    # (step win//8, centre-first) then cover any residual phase offset.
    scale_order = [1.0, 0.75, 0.625, 0.5, 0.375, 0.25, 0.1875, 0.125, 1.25, 1.5, 2.0]
    per_scale_budget = 45  # attempts allowed per scale bucket, keeps one scale from starving others
    attempts = 0
    for scale in scale_order:
        win = max(224, int(TILE * scale))
        if win > min(w, h):
            continue
        grid_windows: list[tuple[int, int]] = [
            (gx, gy)
            for gy in range(0, h - win + 1, win)
            for gx in range(0, w - win + 1, win)
        ]
        step = max(96, win // 8)
        fine: list[tuple[int, int]] = []
        seen_fine: set[tuple[int, int]] = set()
        for gy in range(0, h - win + 1, step):
            for gx in range(0, w - win + 1, step):
                if (gx, gy) not in seen_fine:
                    seen_fine.add((gx, gy))
                    fine.append((gx, gy))
        # centre-most windows first: resized images keep the tile grid centred around
        # the image centre, and crops keep enough of the centre for a hit.
        fine.sort(key=lambda c: abs(c[0] + win / 2 - w / 2) + abs(c[1] + win / 2 - h / 2))
        for x, y in grid_windows + fine[:per_scale_budget]:
            if attempts >= max_windows:
                return {"detected": False, "method": "exhausted", "expected": expected_hex, "attempts": attempts}
            attempts += 1
            patch = image.crop((x, y, x + win, y + win))
            if _decode_ok(tm_plain, patch, expected):
                return {"detected": True, "method": "window", "expected": expected_hex, "attempts": attempts, "window": [x, y, win]}
    return {"detected": False, "method": "exhausted", "expected": expected_hex, "attempts": attempts}


def main() -> int:
    args = sys.argv[1:]
    if len(args) < 3:
        print(json.dumps({"error": "usage: runner embed|extract <path> <path> [hex]"}), file=sys.stderr)
        return 2
    command = args[0]
    try:
        if command == "embed" and len(args) == 4:
            result = embed(Path(args[1]), Path(args[2]), int(args[3], 16))
        elif command == "extract" and len(args) == 3:
            result = extract(Path(args[1]), args[2])
        else:
            print(json.dumps({"error": "usage: runner embed <src> <dst> <hex> | extract <src> <hex>"}), file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001 - runner boundary must surface any failure as JSON error
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
