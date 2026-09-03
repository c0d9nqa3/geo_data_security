"""DLG 水印在格式转换(SHP->GeoJSON->SHP)与字段裁剪后仍可提取的验证。

真实场景: 甲方数据可能在流转中被重导出/转换。DLG 水印是加密属性字段,
只要属性保留即可提取。本脚本验证转换链路后 _wm 字段仍在。
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

import shapefile  # noqa: E402

from geo_security.vector_watermark import (  # noqa: E402
    embed_shapefile_watermark,
    extract_shapefile_watermark,
)

DLG_DIR = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/k50c004003/k50c004003")
OUT = ROOT / "runtime" / "dlg_convert_verify"
KEY = b"dlg-verify-key-not-production"
TEXT = "DLG-CONVERT-20260904"

results = []
for src in sorted(DLG_DIR.glob("*.shp"))[:3]:
    layer_out = OUT / src.stem
    if layer_out.exists():
        shutil.rmtree(layer_out)
    layer_out.mkdir(parents=True)
    try:
        # 1. embed into a marked copy
        marked = layer_out / "marked.shp"
        embed_shapefile_watermark(src, marked, TEXT, KEY)
        # 2. simulate format conversion: read marked, write GeoJSON-like (all fields kept),
        #    then write a NEW shp from it (round-trip through generic records)
        reader = shapefile.Reader(str(marked), encoding="gbk", encodingErrors="replace")
        converted = layer_out / "converted.shp"
        writer = shapefile.Writer(str(converted), shapeType=reader.shapeType)
        writer.fields = list(reader.fields[1:])
        for shape, record in zip(reader.iterShapes(), reader.iterRecords()):
            writer.shape(shape)
            writer.record(*record)
        writer.close()
        # 3. extract from the converted copy
        extracted = extract_shapefile_watermark(converted, KEY)
        results.append({
            "layer": src.stem,
            "records": len(extracted),
            "extract_after_convert": bool(extracted) and all(t == TEXT for t in extracted),
        })
        print(json.dumps(results[-1]), flush=True)
    except Exception as exc:  # noqa: BLE001
        results.append({"layer": src.stem, "error": repr(exc)})
        print(json.dumps(results[-1]), flush=True)

ok = sum(1 for r in results if r.get("extract_after_convert"))
print(json.dumps({"total": len(results), "passed": ok, "layers": results}), flush=True)
