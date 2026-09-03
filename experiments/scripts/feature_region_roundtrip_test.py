from pathlib import Path
import sys

import cv2
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.feature_robust_watermark import _DELTA, _decode_patch, _embed_patch, _features, _normalized_patch

REAL_B1 = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/lt51470342011231khc00/LT51470342011231KHC00_B1.TIF")


def test_feature_roundtrip_uses_inverse_mapping_without_false_relocalization():
    with rasterio.open(REAL_B1) as dataset:
        data = dataset.read(1)
    point = _features(data, limit=1)[0]
    patch, forward = _normalized_patch(data, point)
    marked = _embed_patch(patch, 0xA5A5F00D, _DELTA)
    inverse = cv2.invertAffineTransform(forward)
    candidate = data.copy()
    region = cv2.warpAffine(marked, inverse, (data.shape[1], data.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    mask = cv2.warpAffine(np.ones_like(marked, dtype=np.uint8), inverse, (data.shape[1], data.shape[0]), flags=cv2.INTER_NEAREST)
    candidate[mask > 0] = region[mask > 0]
    recovered, _ = _normalized_patch(candidate, point)
    value, _ = _decode_patch(recovered, _DELTA)
    assert value == 0xA5A5F00D
