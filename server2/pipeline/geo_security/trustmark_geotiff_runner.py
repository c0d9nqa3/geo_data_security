"""TrustMark 瓦片 GeoTIFF 水印 runner（由独立 trustmark venv 的 python 执行）。

主项目环境 numpy>=2 与 torch 2.1.2 冲突，因此本 runner 必须用
runtime/trustmark_venv/Scripts/python.exe 执行（该环境 numpy<2 + torch 2.1.2+cpu +
trustmark 0.9.0 editable + rasterio + pyproj）。

用法:
    trustmark_geotiff_runner.py embed <source.tif> <dest.tif> <hex_watermark>
    trustmark_geotiff_runner.py extract <source.tif> <expected_hex>

约定:
- GeoTIFF 单波段灰度; 复制为 RGB 供 TrustMark; 嵌入后取 R 通道写回原 profile。
- 1024x1024 瓦片网格, 每瓦片独立嵌入同一 40bit BCH_SUPER 码字(32bit 业务位)。
- 保留原 dtype/CRS/transform/tags, 并写入 GDS_TM_SRC_CRS/TF/W/H 记录原空间参考。
- extract: 先读记录的原空间参考; 若当前 CRS 不同(重投影攻击)则 GDAL 逆投影回原网格;
  然后 bbox 检测 + 多尺度网格/细滑窗口解码。stdout 单行 JSON; 失败非零退出。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import Affine
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
    tf = profile.get("transform")
    tags["GDS_TM_ENGINE"] = "TrustMark-Q-TILED1024"
    tags["GDS_TM_ECC"] = "BCH_SUPER"
    tags[EXPECTED_HEX_TAG] = format(watermark, "08X")
    tags["GDS_TM_SRC_W"] = str(w)
    tags["GDS_TM_SRC_H"] = str(h)
    if profile.get("crs") is not None:
        tags["GDS_TM_SRC_CRS"] = str(profile["crs"].to_string() if hasattr(profile["crs"], "to_string") else profile["crs"])
    if tf is not None:
        tags["GDS_TM_SRC_TF"] = ",".join(str(round(float(v), 12)) for v in (tf.a, tf.b, tf.c, tf.d, tf.e, tf.f))
    with rasterio.open(destination, "w", **profile) as ds:
        ds.update_tags(**tags)
        ds.write(marked[:, :, 0].astype(np.uint8), 1)
    return {"tiles": tiles, "psnr_db": round(psnr, 3), "dtype": str(np.uint8), "width": w, "height": h}


def _read_orig_georef(source: Path) -> dict:
    """Read recorded original georeferencing written at embed time (may be absent)."""
    try:
        with rasterio.open(source) as ds:
            tags = ds.tags()
        out = {
            "crs": tags.get("GDS_TM_SRC_CRS"),
            "tf": tags.get("GDS_TM_SRC_TF"),
            "w": tags.get("GDS_TM_SRC_W"),
            "h": tags.get("GDS_TM_SRC_H"),
        }
        return {k: v for k, v in out.items() if v is not None}
    except Exception:
        return {}


def _warp_back_to_orig_grid(source: Path, orig: dict) -> np.ndarray:
    """Reproject attacked image onto the recorded original CRS/grid via GDAL.

    Exact inverse of the warp attack: destination transform == recorded original
    transform and destination size == recorded original size, so the embedded
    1024-px tile grid aligns perfectly afterwards.
    """
    from rasterio.warp import reproject

    with rasterio.open(source) as ds:
        current_crs = ds.crs
        current_tf = ds.transform
        data = ds.read(1)
    if current_crs is None:
        raise ValueError("attacked image has no CRS; cannot reproject back")
    orig_crs = rasterio.crs.CRS.from_string(orig["crs"])
    if str(current_crs) == str(orig_crs):
        raise ValueError("CRS already matches original; no warp needed")
    tf_parts = [float(v) for v in orig["tf"].split(",")]
    orig_tf = Affine(*tf_parts)
    out_width, out_height = int(orig["w"]), int(orig["h"])
    destination = np.empty((out_height, out_width), dtype=np.uint8)
    reproject(
        source=data,
        destination=destination,
        src_transform=current_tf,
        src_crs=current_crs,
        dst_transform=orig_tf,
        dst_crs=orig_crs,
        resampling=Resampling.bilinear,
    )
    return destination


def _decode_ok(tm: TrustMark, image: Image.Image, expected: int) -> bool:
    bits, present, schema = tm.decode(image.convert("RGB"), MODE="binary")
    return bool(present) and len(bits) >= 32 and int(bits[:32], 2) == expected


def extract(source: Path, expected_hex: str, max_windows: int = 400) -> dict:
    source = Path(source)
    expected = int(expected_hex, 16)
    orig = _read_orig_georef(source)
    needs_warp = bool(orig) and "crs" in orig and "tf" in orig and "w" in orig and "h" in orig
    with rasterio.open(source) as ds:
        current_crs = str(ds.crs) if ds.crs is not None else ""
        data = ds.read(1)
    if needs_warp and "crs" in orig and current_crs and current_crs != orig["crs"]:
        try:
            data = _warp_back_to_orig_grid(source, orig)
        except Exception:
            pass  # fall through to direct scanning of the attacked image
    w, h = data.shape[1], data.shape[0]
    rgb = np.repeat(data[:, :, None], 3, axis=2)
    image = Image.fromarray(rgb, mode="RGB")
    tm_det = _make_tm(load_bbox=True)
    tm_plain = _make_tm()
    # prong 1: bbox detect over whole image
    try:
        bits, present, schema = tm_det.decode(image.convert("RGB"), MODE="binary", DETECTFIRST=True)
        if present and len(bits) >= 32 and int(bits[:32], 2) == expected:
            return {"detected": True, "method": "bbox_detect", "expected": expected_hex, "warped": needs_warp}
    except Exception:
        pass
    # prong 2: multi-scale windows. Buckets ordered by likelihood: original 1024 tile
    # first (full/crop/JPEG/noise keep tile size), then shrinking (resize-down), then
    # growing (resize-up). Each bucket gets a budget so one scale cannot starve others.
    scale_order = [1.0, 0.75, 0.625, 0.5, 0.375, 0.25, 0.1875, 0.125, 1.25, 1.5, 2.0]
    per_scale_budget = 45
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
                return {"detected": False, "method": "exhausted", "expected": expected_hex, "attempts": attempts, "warped": needs_warp}
            attempts += 1
            patch = image.crop((x, y, x + win, y + win))
            if _decode_ok(tm_plain, patch, expected):
                return {"detected": True, "method": "window", "expected": expected_hex, "attempts": attempts, "window": [x, y, win], "warped": needs_warp}
    return {"detected": False, "method": "exhausted", "expected": expected_hex, "attempts": attempts, "warped": needs_warp}


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
