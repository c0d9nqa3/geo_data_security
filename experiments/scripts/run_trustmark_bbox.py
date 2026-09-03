from pathlib import Path
import sys
import json
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "trustmark_source" / "python"))
from trustmark import TrustMark

OUT = ROOT / "runtime" / "trustmark_matrix_b1"
EXPECTED = 0xA5A5F00D

def decode_bits(tm, image):
    bits, present, schema = tm.decode(image.convert("RGB"), MODE="binary", DETECTFIRST=True)
    value = int(bits[:32], 2) if present and len(bits) >= 32 else None
    return value, present, schema

tm = TrustMark(verbose=True, model_type="Q", encoding_type=TrustMark.Encoding.BCH_SUPER, loadRemover=False, loadBBoxDetector=True)
base = Image.open(OUT / "source_rgb.png").convert("RGB") if (OUT / "source_rgb.png").exists() else None
if base is None:
    print(json.dumps({"error":"source_rgb.png missing"}))
    raise SystemExit(2)
rows=[]
for path in sorted(OUT.glob("attack_*.png")):
    started=time.perf_counter()
    try:
        value,present,schema=decode_bits(tm,Image.open(path)); row={"file":path.name,"value":None if value is None else hex(value),"ok":value==EXPECTED,"present":present,"schema":schema,"seconds":round(time.perf_counter()-started,3)}
    except Exception as exc: row={"file":path.name,"ok":False,"error":repr(exc)}
    rows.append(row);print(json.dumps(row,ensure_ascii=False))
print(json.dumps({"count":len(rows),"passed":sum(x["ok"] for x in rows),"rate":sum(x["ok"] for x in rows)/len(rows) if rows else 0},ensure_ascii=False))
