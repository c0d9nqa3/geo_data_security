from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _round_coordinates(value: Any, decimals: int) -> Any:
    if isinstance(value, list):
        if value and all(isinstance(item, (int, float)) for item in value):
            return [round(float(item), decimals) for item in value]
        return [_round_coordinates(item, decimals) for item in value]
    return value


def reduce_geojson_precision(source: Path, destination: Path, decimals: int) -> None:
    if decimals < 0 or decimals > 15:
        raise ValueError("decimals must be between 0 and 15")
    document = json.loads(Path(source).read_text(encoding="utf-8"))
    if document.get("type") == "FeatureCollection":
        features = document.get("features", [])
    elif document.get("type") == "Feature":
        features = [document]
    else:
        raise ValueError("GeoJSON must be a Feature or FeatureCollection")
    for feature in features:
        geometry = feature.get("geometry") or {}
        if "coordinates" in geometry:
            geometry["coordinates"] = _round_coordinates(geometry["coordinates"], decimals)
    Path(destination).write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
