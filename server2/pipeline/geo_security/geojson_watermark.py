from __future__ import annotations

import json
from pathlib import Path

from .crypto import decrypt_text, encrypt_text


def _walk_features(value: dict) -> list[dict]:
    if value.get("type") == "FeatureCollection":
        return [item for item in value.get("features", []) if item.get("type") == "Feature"]
    if value.get("type") == "Feature":
        return [value]
    raise ValueError("GeoJSON must be a Feature or FeatureCollection")


def embed_geojson_watermark(source: Path, destination: Path, text: str, key: bytes) -> int:
    document = json.loads(Path(source).read_text(encoding="utf-8"))
    features = _walk_features(document)
    for feature in features:
        properties = feature.setdefault("properties", {})
        if "_wm" in properties:
            raise ValueError("source already contains reserved property _wm")
        properties["_wm"] = encrypt_text(text, key)
    Path(destination).write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(features)


def extract_geojson_watermark(source: Path, key: bytes) -> list[str]:
    document = json.loads(Path(source).read_text(encoding="utf-8"))
    values = []
    for feature in _walk_features(document):
        properties = feature.get("properties") or {}
        if "_wm" not in properties:
            raise ValueError("watermark property _wm not found")
        values.append(decrypt_text(properties["_wm"], key))
    return values
