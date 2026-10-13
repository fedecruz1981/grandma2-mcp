import json, sys
from pathlib import Path
D = Path("data")
cues = json.loads((D/"pdf_cues.json").read_text(encoding="utf-8"))
out = []
for q in sorted(cues, key=lambda k: int(k[1:])):
    c = cues[q]
    if not c["scene"].startswith("ESCENA 1"):
        continue
    out.append(f"{q}  {c['scene']}")
    out.append(f"   momento : {c['momento']!r}")
    for col in ("BF","BM","BT","CM","CM2","HUMO","humo","efecto","notas"):
        if col in c:
            out.append(f"   {col:<8}: {c[col]!r}")
    out.append(f"   claves  : {sorted(c.keys())}")
    out.append("")
(D/"_scene1_raw.txt").write_text("\n".join(out), encoding="utf-8")
print("ok", len(out), "lineas")
