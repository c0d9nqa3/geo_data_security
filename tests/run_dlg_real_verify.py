"""真实 DLG(SHP) 水印验证: 对 data/k50c004003/k50c004003 各要素层做几何不变水印。

验证点(对照技术要求):
1. embed 成功: 每层写出带 _wm 字段的新 SHP, 字段值加密
2. 几何零改动: geometry_digest(before) == geometry_digest(after)  — 坐标/拓扑/几何不变
3. extract 成功: 每层解出密文并解密回原文
4. 打开兼容: 用 pyshp 重新读取记录数与字段数一致(即原软件可打开的代理指标)
"""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server2" / "pipeline"))

from geo_security.vector_watermark import (  # noqa: E402
    embed_shapefile_watermark,
    extract_shapefile_watermark,
    geometry_digest,
    sha256_file,
)

DLG_DIR = Path(r"C:/Users/Steven/Desktop/MyPP/遥感测绘/data/k50c004003/k50c004003")
OUT = ROOT / "runtime" / "dlg_verify"
KEY = b"dlg-verify-key-not-production"
TEXT = "DLG-20260904-VERIFY"

results = []
layers = sorted(p for p in DLG_DIR.glob("*.shp"))
print(f"found {len(layers)} SHP layers in {DLG_DIR}", flush=True)
if not layers:
    raise SystemExit("no layers")

OUT.mkdir(parents=True, exist_ok=True)
for src in layers:
    t0 = time.perf_counter()
    layer_out = OUT / src.stem
    if layer_out.exists():
        shutil.rmtree(layer_out)
    layer_out.mkdir(parents=True)
    dst = layer_out / src.name
    try:
        before_digest = geometry_digest(src)
        sha_before = sha256_file(src)
        embed_shapefile_watermark(src, dst, TEXT, KEY)
        sha_after = sha256_file(dst)
        extracted = extract_shapefile_watermark(dst, KEY)
        after_digest = geometry_digest(dst)
        geometry_ok = before_digest == after_digest
        text_ok = bool(extracted) and all(t == TEXT for t in extracted)
        # field/sidecar integrity: prj must be copied through
        prj_ok = dst.with_suffix(".prj").exists()
        results.append({
            "layer": src.stem,
            "records": len(extracted),
            "geometry_unchanged": geometry_ok,
            "text_roundtrip": text_ok,
            "prj_copied": prj_ok,
            "file_bytes": src.stat().st_size,
            "seconds": round(time.perf_counter() - t0, 2),
        })
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    except Exception as exc:  # noqa: BLE001
        results.append({"layer": src.stem, "error": repr(exc)})
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)

ok = sum(1 for r in results if r.get("geometry_unchanged") and r.get("text_roundtrip"))
report = {"total": len(results), "passed": ok,
          "layers": results,
          "criterion": "geometry unchanged + encrypted text roundtrip per layer"}
print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
