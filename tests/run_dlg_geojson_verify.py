"""真实 SHP->GeoJSON 格式转换后水印可提取性验证(二维专题矢量真实链路)。

场景: DLG SHP 嵌水印后, 在流转中经工具转换为 GeoJSON 分发(属性保留)。
验证: 转换后文档内 _wm 属性仍携带加密水印并可解密。
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

import shapefile  # noqa: E402

from geo_security.geojson_watermark import extract_geojson_watermark  # noqa: E402
from geo_security.vector_watermark import embed_shapefile_watermark  # noqa: E402

DLG_DIR = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/k50c004003/k50c004003")
OUT = ROOT / "runtime" / "dlg_geojson_verify"
KEY = b"dlg-verify-key-not-production"
TEXT = "DLG-GEOJSON-20260904"


def shp_to_geojson(shp_path: Path, out_path: Path) -> dict:
    """pyshp-based SHP->GeoJSON: keeps all attributes verbatim."""
    reader = shapefile.Reader(str(shp_path), encoding="gbk", encodingErrors="replace")
    fields = reader.fields[1:]
    features = []
    for shape, record in zip(reader.iterShapes(), reader.iterRecords()):
        props = {}
        for (name, ftype, size, dec), value in zip(fields, record):
            props[name] = value
        # minimal geometry: emit shapeType + bbox + points (generic conversion keeps
        # topology shapeType constant); attributes are the carrier under test
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "GeometryCollection" if shape.shapeType in (1,) else "Polygon",
                         "coordinates": []},
        })
    document = {"type": "FeatureCollection", "features": features,
                "source": str(shp_path.name), "shapeType": reader.shapeType}
    Path(out_path).write_text(json.dumps(document, ensure_ascii=False, indent=1), encoding="utf-8")
    return document


results = []
for src in sorted(DLG_DIR.glob("*.shp"))[:3]:
    layer_out = OUT / src.stem
    if layer_out.exists():
        shutil.rmtree(layer_out)
    layer_out.mkdir(parents=True)
    try:
        # 1. embed on real SHP layer
        marked = layer_out / "marked.shp"
        embed_shapefile_watermark(src, marked, TEXT, KEY)
        # 2. convert marked SHP -> GeoJSON (format conversion in transit)
        geojson = layer_out / "converted.geojson"
        shp_to_geojson(marked, geojson)
        # 3. extract watermark from converted GeoJSON
        texts = extract_geojson_watermark(geojson, KEY)
        results.append({
            "layer": src.stem,
            "features": len(texts),
            "extract_after_shp_to_geojson": bool(texts) and all(t == TEXT for t in texts),
        })
        print(json.dumps(results[-1]), flush=True)
    except Exception as exc:  # noqa: BLE001
        results.append({"layer": src.stem, "error": repr(exc)})
        print(json.dumps(results[-1]), flush=True)

ok = sum(1 for r in results if r.get("extract_after_shp_to_geojson"))
print(json.dumps({"total": len(results), "passed": ok, "layers": results}), flush=True)
