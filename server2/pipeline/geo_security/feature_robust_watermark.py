from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
import rasterio
from scipy.fft import dctn, idctn

_PATCH = 128
_BITS = 32
_REPEATS = 4
_DELTA = 8.0
_TAG_DELTA = "GDS_FEATURE_DELTA"
_TAG_VERSION = "GDS_FEATURE_VERSION"


def _bits(value: int) -> np.ndarray:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("watermark must be an unsigned 32-bit integer")
    return np.array([(value >> (31 - i)) & 1 for i in range(_BITS)], dtype=np.uint8)


def _load(path: Path) -> tuple[np.ndarray, dict, dict]:
    with rasterio.open(path) as dataset:
        return dataset.read(1), dataset.profile.copy(), dataset.tags()


def _save(path: Path, data: np.ndarray, profile: dict, tags: dict) -> None:
    profile.update(dtype="uint8", count=1)
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.update_tags(**tags)
        dataset.write(data.astype(np.uint8), 1)


def _gray_thumbnail(data: np.ndarray) -> tuple[np.ndarray, float]:
    scale = min(1.0, 1200.0 / max(data.shape))
    thumb = cv2.resize(data, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else data
    return cv2.normalize(thumb, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8), scale


def _features(data: np.ndarray, limit: int = 24) -> list[cv2.KeyPoint]:
    thumb, scale = _gray_thumbnail(data)
    sift = cv2.SIFT_create(nfeatures=max(800, limit * 100), contrastThreshold=0.01)
    keypoints = sift.detect(thumb, None)
    result: list[cv2.KeyPoint] = []
    half = _PATCH // 2
    for point in sorted(keypoints, key=lambda item: item.response, reverse=True):
        point.pt = (point.pt[0] / scale, point.pt[1] / scale)
        point.size = point.size / scale
        x, y = point.pt
        if y < half or x < half or y + half >= data.shape[0] or x + half >= data.shape[1]:
            continue
        if all((y - old.pt[1]) ** 2 + (x - old.pt[0]) ** 2 >= (_PATCH * 0.9) ** 2 for old in result):
            result.append(point)
        if len(result) >= limit:
            break
    return result


def _normalized_patch(data: np.ndarray, point: cv2.KeyPoint, inverse: bool = False) -> tuple[np.ndarray, np.ndarray]:
    # SIFT keypoint size is approximately the diameter of the stable region.
    # Use a minimum radius for small keypoints and normalize orientation.
    size = max(float(point.size) * 4.0, 64.0)
    matrix = cv2.getRotationMatrix2D(point.pt, -float(point.angle), _PATCH / size)
    matrix[0, 2] += _PATCH / 2.0 - point.pt[0]
    matrix[1, 2] += _PATCH / 2.0 - point.pt[1]
    if inverse:
        matrix = cv2.invertAffineTransform(matrix)
    if inverse:
        patch = cv2.warpAffine(data, matrix, (int(round(size)), int(round(size))), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    else:
        patch = cv2.warpAffine(data, matrix, (_PATCH, _PATCH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return patch, matrix


def _coords() -> list[tuple[int, int]]:
    base = [(10 + (i % 8) * 5, 12 + (i // 8) * 5) for i in range(_BITS)]
    return base * _REPEATS


def _embed_patch(patch: np.ndarray, watermark: int, delta: float) -> np.ndarray:
    coeff = dctn(patch.astype(np.float32), norm="ortho")
    bits = _bits(watermark)
    for index, (row, col) in enumerate(_coords()):
        bit = int(bits[index % _BITS])
        a, b = float(coeff[row, col]), float(coeff[row + 1, col + 1])
        middle = (a + b) / 2.0
        sign = 1.0 if bit else -1.0
        coeff[row, col] = middle + sign * delta / 2.0
        coeff[row + 1, col + 1] = middle - sign * delta / 2.0
    return np.clip(np.rint(idctn(coeff, norm="ortho")), 0, 255).astype(np.uint8)


def _decode_patch(patch: np.ndarray, delta: float) -> tuple[int, float]:
    coeff = dctn(patch.astype(np.float32), norm="ortho")
    votes = np.zeros((_BITS, 2), dtype=np.int32)
    for index, (row, col) in enumerate(_coords()):
        difference = float(coeff[row, col] - coeff[row + 1, col + 1])
        votes[index % _BITS, int(difference > 0)] += 1
    value = 0
    for index in range(_BITS):
        value = (value << 1) | int(votes[index, 1] > votes[index, 0])
    confidence = float(np.mean(np.abs(votes[:, 1] - votes[:, 0])))
    return value, confidence


def embed_feature_watermark(source: Path, destination: Path, watermark: int) -> float:
    data, profile, tags = _load(Path(source))
    if profile["dtype"] != "uint8" or profile.get("count", 1) != 1:
        raise ValueError("feature watermark currently requires one uint8 band")
    points = _features(data)
    if len(points) < 4:
        raise ValueError("not enough stable feature regions")
    output = data.copy()
    for point in points:
        patch, _ = _normalized_patch(data, point)
        marked = _embed_patch(patch, watermark, _DELTA)
        _, inverse = _normalized_patch(data, point, inverse=True)
        # Project the canonical marked patch back into the source image.
        restored = cv2.warpAffine(marked, inverse, (data.shape[1], data.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        mask = cv2.warpAffine(np.ones_like(marked, dtype=np.uint8), inverse, (data.shape[1], data.shape[0]), flags=cv2.INTER_LINEAR)
        valid = mask > 0
        output[valid] = restored[valid]
    tags.update({_TAG_DELTA: repr(_DELTA), _TAG_VERSION: "3"})
    _save(Path(destination), output, profile, tags)
    mse = float(np.mean((data.astype(np.float64) - output.astype(np.float64)) ** 2))
    peak = float(np.max(data) - np.min(data)) or 1.0
    return float("inf") if mse == 0 else 20.0 * math.log10(peak / math.sqrt(mse))


def extract_feature_watermark(source: Path) -> int:
    data, _, tags = _load(Path(source))
    delta = float(tags.get(_TAG_DELTA, _DELTA))
    points = _features(data, limit=48)
    if not points:
        raise ValueError("no stable feature region found")
    candidates: list[tuple[int, float]] = []
    for point in points:
        patch, _ = _normalized_patch(data, point)
        candidates.append(_decode_patch(patch, delta))
    grouped: dict[int, list[float]] = {}
    for value, confidence in candidates:
        grouped.setdefault(value, []).append(confidence)
    return max(grouped.items(), key=lambda item: (len(item[1]), np.mean(item[1])))[0]
