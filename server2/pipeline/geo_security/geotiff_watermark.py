from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pywt
import rasterio
from scipy.fft import dct, idct


_BLOCK = 4
_BITS = 32
_TAG_STEP = "GDS_WM_STEP"


def psnr(original: np.ndarray, watermarked: np.ndarray) -> float:
    original = np.asarray(original, dtype=np.float64)
    watermarked = np.asarray(watermarked, dtype=np.float64)
    mse = float(np.mean((original - watermarked) ** 2))
    if mse == 0:
        return float("inf")
    peak = float(np.max(original) - np.min(original)) or 1.0
    return 20.0 * math.log10(peak / math.sqrt(mse))


def _bits(value: int) -> list[int]:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("watermark must be an unsigned 32-bit integer")
    return [(value >> (31 - index)) & 1 for index in range(_BITS)]


def _read_band(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as dataset:
        if dataset.count < 1:
            raise ValueError("GeoTIFF has no bands")
        return dataset.read(1).astype(np.float32), dataset.profile.copy()


def _transform(pixels: np.ndarray) -> tuple[np.ndarray, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    low, details = pywt.dwt2(pixels, "haar")
    diagonal = dct(dct(details[2], axis=0, norm="ortho"), axis=1, norm="ortho")
    return diagonal, (low, details[0], details[1])


def _restore(diagonal: np.ndarray, details: tuple[np.ndarray, np.ndarray, np.ndarray], shape: tuple[int, int]) -> np.ndarray:
    low, horizontal, vertical = details
    restored = idct(idct(diagonal, axis=0, norm="ortho"), axis=1, norm="ortho")
    output = pywt.idwt2((low, (horizontal, vertical, restored)), "haar")
    return output[: shape[0], : shape[1]]


def _blocks(diagonal: np.ndarray):
    rows, cols = diagonal.shape
    for row in range(0, rows - _BLOCK + 1, _BLOCK):
        for col in range(0, cols - _BLOCK + 1, _BLOCK):
            yield row, col


def _step(pixels: np.ndarray, dtype: str) -> float:
    data_range = float(np.max(pixels) - np.min(pixels)) or 1.0
    if dtype == "uint8":
        # Integer serialization needs a much larger coefficient displacement
        # to survive rounding back to bytes.
        return max(data_range * 4.0, 1024.0)
    return max(data_range * 0.04, 8.0)


def _modify(diagonal: np.ndarray, watermark: int, step: float) -> np.ndarray:
    output = diagonal.copy()
    bits = _bits(watermark)
    for index, (row, col) in enumerate(_blocks(output)):
        if index >= _BITS:
            break
        block = output[row:row + _BLOCK, col:col + _BLOCK]
        u, singular, vt = np.linalg.svd(block, full_matrices=False)
        # Quantize the leading singular value. Odd/even bucket represents the bit.
        bucket = max(0, int(math.floor(float(singular[0]) / step)))
        if bucket % 2 != bits[index]:
            bucket += 1
        singular[0] = (bucket + 0.5) * step
        output[row:row + _BLOCK, col:col + _BLOCK] = (u * singular) @ vt
    return output


def embed_geotiff_watermark(source: Path, destination: Path, watermark: int) -> float:
    source = Path(source)
    pixels, profile = _read_band(source)
    original_dtype = profile["dtype"]
    original_tags = {}
    with rasterio.open(source) as dataset:
        original_tags = dataset.tags()
    diagonal, details = _transform(pixels)
    step = _step(pixels, original_dtype)
    modified = _modify(diagonal, watermark, step)
    output = _restore(modified, details, pixels.shape)
    if original_dtype == "uint8":
        output = np.clip(np.rint(output), 0, 255).astype(np.uint8)
        output_dtype = "uint8"
    else:
        output = output.astype(original_dtype)
        output_dtype = original_dtype
    profile.update(dtype=output_dtype, count=1)
    with rasterio.open(destination, "w", **profile) as dataset:
        dataset.update_tags(**original_tags)
        dataset.update_tags(**{_TAG_STEP: repr(step)})
        dataset.write(output, 1)
    return psnr(pixels, output)


def extract_geotiff_watermark(source: Path) -> int:
    source = Path(source)
    pixels, profile = _read_band(source)
    dtype = profile["dtype"]
    with rasterio.open(source) as dataset:
        raw_step = dataset.tags().get(_TAG_STEP)
    step = float(raw_step) if raw_step else _step(pixels, dtype)
    diagonal, _ = _transform(pixels)
    bits: list[int] = []
    for row, col in _blocks(diagonal):
        if len(bits) >= _BITS:
            break
        block = diagonal[row:row + _BLOCK, col:col + _BLOCK]
        _, singular, _ = np.linalg.svd(block, full_matrices=False)
        bits.append(max(0, int(math.floor(float(singular[0]) / step))) % 2)
    if len(bits) != _BITS:
        raise ValueError("GeoTIFF band is too small for a 32-bit watermark")
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value
