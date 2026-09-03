from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window
from scipy.fft import dctn, idctn

_TILE = 512
_BLOCK = 8
_BITS = 32
_STEP_TAG = "GDS_ROBUST_STEP"
_TILE_TAG = "GDS_ROBUST_TILE"
_ORIGIN_C = "GDS_ROBUST_ORIGIN_C"
_ORIGIN_F = "GDS_ROBUST_ORIGIN_F"
_PIXEL_A = "GDS_ROBUST_PIXEL_A"
_PIXEL_E = "GDS_ROBUST_PIXEL_E"


def _bits(value: int) -> np.ndarray:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("watermark must be an unsigned 32-bit integer")
    return np.array([(value >> (31 - index)) & 1 for index in range(_BITS)], dtype=np.uint8)


def _tile_dct(tile: np.ndarray) -> np.ndarray:
    return dctn(tile.astype(np.float32), axes=(-2, -1), norm="ortho")


def _tile_idct(coeff: np.ndarray) -> np.ndarray:
    return idctn(coeff, axes=(-2, -1), norm="ortho")


def _coefficient_position(index: int) -> tuple[int, int]:
    block_row = index // 8
    block_col = index % 8
    return block_row * _BLOCK, block_col * _BLOCK


def _set_qim(value: float, bit: int, step: float) -> float:
    # Signed QIM: parity is applied to the absolute bucket, then sign is kept.
    sign = -1.0 if value < 0 else 1.0
    bucket = math.floor(abs(value) / step)
    if bucket % 2 != int(bit):
        bucket += 1
    return sign * (bucket + 0.5) * step


def _read_qim(value: float, step: float) -> tuple[int, float]:
    ratio = abs(float(value)) / step
    bucket = math.floor(ratio)
    return bucket % 2, abs(ratio - (bucket + 0.5))


def _embed_tile(tile: np.ndarray, watermark: int, step: float) -> np.ndarray:
    if float(np.std(tile)) < 2.0:
        return tile.copy()
    coeff = _tile_dct(tile)
    bits = _bits(watermark)
    # 64 carrier blocks; each bit is repeated twice for local majority voting.
    for carrier_index in range(64):
        bit_index = carrier_index % _BITS
        row, col = _coefficient_position(carrier_index)
        block = coeff[row:row + _BLOCK, col:col + _BLOCK]
        u, singular, vt = np.linalg.svd(block, full_matrices=False)
        singular[0] = _set_qim(float(singular[0]), int(bits[bit_index]), step)
        coeff[row:row + _BLOCK, col:col + _BLOCK] = (u * singular) @ vt
    output = _tile_idct(coeff)
    return np.clip(np.rint(output), 0, 255).astype(np.uint8)


def _decode_tile(tile: np.ndarray, step: float) -> tuple[int, float, bool]:
    if float(np.std(tile)) < 2.0:
        return 0, 0.0, False
    coeff = _tile_dct(tile)
    votes = np.zeros((_BITS, 2), dtype=np.int32)
    margins: list[float] = []
    for carrier_index in range(64):
        row, col = _coefficient_position(carrier_index)
        singular = np.linalg.svd(coeff[row:row + _BLOCK, col:col + _BLOCK], compute_uv=False)[0]
        bit, margin = _read_qim(float(singular), step)
        votes[carrier_index % _BITS, bit] += 1
        margins.append(margin)
    value = 0
    for bit_index in range(_BITS):
        value = (value << 1) | int(votes[bit_index, 1] > votes[bit_index, 0])
    confidence = float(np.mean(np.abs(votes[:, 1] - votes[:, 0])))
    return value, confidence, True


def _step(data: np.ndarray) -> float:
    data_range = float(np.max(data) - np.min(data)) or 1.0
    return 48.0 if data.dtype == np.uint8 else max(data_range * 0.04, 8.0)


def embed_geotiff_watermark_robust(source: Path, destination: Path, watermark: int) -> float:
    source = Path(source)
    with rasterio.open(source) as dataset:
        if dataset.count != 1 or dataset.dtypes[0] != "uint8":
            raise ValueError("robust carrier currently requires one uint8 band")
        data = dataset.read(1)
        profile = dataset.profile.copy()
        tags = dataset.tags()
        transform = dataset.transform
    step = _step(data)
    output = data.copy()
    for row in range(0, data.shape[0] - _TILE + 1, _TILE):
        for col in range(0, data.shape[1] - _TILE + 1, _TILE):
            output[row:row + _TILE, col:col + _TILE] = _embed_tile(data[row:row + _TILE, col:col + _TILE], watermark, step)
    tags.update({
        _STEP_TAG: repr(step), _TILE_TAG: str(_TILE),
        _ORIGIN_C: repr(transform.c), _ORIGIN_F: repr(transform.f),
        _PIXEL_A: repr(transform.a), _PIXEL_E: repr(transform.e),
    })
    with rasterio.open(destination, "w", **profile) as dataset:
        dataset.update_tags(**tags)
        dataset.write(output, 1)
    mse = float(np.mean((data.astype(np.float64) - output.astype(np.float64)) ** 2))
    peak = float(np.max(data) - np.min(data)) or 1.0
    return float("inf") if mse == 0 else 20.0 * math.log10(peak / math.sqrt(mse))


def _grid_mapping(dataset: rasterio.DatasetReader) -> tuple[float, float, float]:
    tags = dataset.tags()
    origin_c = float(tags.get(_ORIGIN_C, dataset.transform.c))
    origin_f = float(tags.get(_ORIGIN_F, dataset.transform.f))
    pixel_a = float(tags.get(_PIXEL_A, dataset.transform.a))
    pixel_e = float(tags.get(_PIXEL_E, dataset.transform.e))
    if pixel_a == 0 or pixel_e == 0:
        raise ValueError("invalid GeoTIFF pixel transform")
    scale_x = dataset.transform.a / pixel_a
    scale_y = dataset.transform.e / pixel_e
    if scale_x <= 0 or scale_y <= 0 or abs(scale_x - scale_y) > 0.05:
        raise ValueError("unsupported non-uniform scale")
    source_row = (origin_f - dataset.transform.f) / (-pixel_e)
    source_col = (dataset.transform.c - origin_c) / pixel_a
    return source_row, source_col, (scale_x + scale_y) / 2.0


def extract_geotiff_watermark_robust(source: Path) -> int:
    source = Path(source)
    with rasterio.open(source) as dataset:
        step = float(dataset.tags().get(_STEP_TAG, "48.0"))
        source_row, source_col, scale = _grid_mapping(dataset)
        candidates: list[tuple[int, float]] = []
        # Source tiles are on a known 512-pixel grid. Only inspect complete
        # tiles still present after crop, at the recorded scale.
        first_row = max(0, int(math.ceil(source_row / _TILE)) * _TILE)
        first_col = max(0, int(math.ceil(source_col / _TILE)) * _TILE)
        for source_r in range(first_row, first_row + 10000 * _TILE, _TILE):
            current_r = (source_r - source_row) / scale
            if current_r < 0 or current_r + _TILE / scale > dataset.height:
                continue
            for source_c in range(first_col, first_col + 10000 * _TILE, _TILE):
                current_c = (source_c - source_col) / scale
                if current_c < 0 or current_c + _TILE / scale > dataset.width:
                    continue
                window = Window(current_c, current_r, _TILE / scale, _TILE / scale)
                tile = dataset.read(1, window=window, out_shape=(1, _TILE, _TILE), resampling=Resampling.bilinear)
                value, confidence, valid = _decode_tile(tile, step)
                if valid:
                    candidates.append((value, confidence))
                if len(candidates) >= 64:
                    break
            if len(candidates) >= 64:
                break
    if not candidates:
        raise ValueError("no complete robust watermark tile remains")
    counts: dict[int, list[float]] = {}
    for value, confidence in candidates:
        counts.setdefault(value, []).append(confidence)
    return max(counts.items(), key=lambda item: (len(item[1]), np.mean(item[1])))[0]
