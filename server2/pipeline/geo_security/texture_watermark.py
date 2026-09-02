from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.fft import dct, idct


_BLOCK = 8
_BITS = 32
_MARKER = "GDS_TEXTURE_STEP"


def _bits(value: int) -> list[int]:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("watermark must be an unsigned 32-bit integer")
    return [(value >> (31 - index)) & 1 for index in range(_BITS)]


def _transform(channel: np.ndarray) -> np.ndarray:
    return dct(dct(channel.astype(np.float64), axis=0, norm="ortho"), axis=1, norm="ortho")


def _restore(transformed: np.ndarray) -> np.ndarray:
    return idct(idct(transformed, axis=0, norm="ortho"), axis=1, norm="ortho")


def _coordinates(shape: tuple[int, int]):
    rows, cols = shape
    for row in range(0, rows - _BLOCK + 1, _BLOCK):
        for col in range(0, cols - _BLOCK + 1, _BLOCK):
            yield row, col


def embed_texture_watermark(source: Path, destination: Path, watermark: int) -> None:
    source = Path(source)
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        array = np.asarray(rgb).copy()
    channel = _transform(array[:, :, 0])
    coords = list(_coordinates(channel.shape))
    if len(coords) < _BITS:
        raise ValueError("texture is too small for a 32-bit watermark")
    scale = max(float(np.std(array[:, :, 0])), 1.0)
    step = max(scale * 0.5, 4.0)
    for bit, (row, col) in zip(_bits(watermark), coords):
        block = channel[row:row + _BLOCK, col:col + _BLOCK]
        u, singular, vt = np.linalg.svd(block, full_matrices=False)
        bucket = max(0, int(math.floor(float(singular[0]) / step)))
        if bucket % 2 != bit:
            bucket += 1
        singular[0] = (bucket + 0.5) * step
        channel[row:row + _BLOCK, col:col + _BLOCK] = (u * singular) @ vt
    output = array.copy()
    output[:, :, 0] = np.clip(_restore(channel), 0, 255).astype(np.uint8)
    Image.fromarray(output).save(destination)
    with Image.open(destination) as saved:
        saved.info[_MARKER] = repr(step)


def extract_texture_watermark(source: Path) -> int:
    with Image.open(source) as image:
        array = np.asarray(image.convert("RGB"))
    channel = _transform(array[:, :, 0])
    coords = list(_coordinates(channel.shape))
    if len(coords) < _BITS:
        raise ValueError("texture is too small for a 32-bit watermark")
    scale = max(float(np.std(array[:, :, 0])), 1.0)
    step = max(scale * 0.5, 4.0)
    value = 0
    for row, col in coords[:_BITS]:
        block = channel[row:row + _BLOCK, col:col + _BLOCK]
        _, singular, _ = np.linalg.svd(block, full_matrices=False)
        bit = max(0, int(math.floor(float(singular[0]) / step))) % 2
        value = (value << 1) | bit
    return value
