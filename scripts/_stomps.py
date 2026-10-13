import json, re
from pathlib import Path
cues = json.loads(Path("data/pdf_cues.json").read_text(encoding="utf-8"))
pat = re.compile(r"stomp|strob|flash|parpad|chase|barrid|titil|arcoiris|arco iris|multicolor|rotand|rotacion", re.I)
print("cues que mencionan movimiento/stomps:")
for q in sorted(cues, key=lambda k: int(k[1:])):
    c = cues[q]
    hits = []
    for col in ("BF","BM","BT","CM"):
        v = c.get(col) or ""
        if pat.search(v):
            hits.append(f"{col}={v!r}")
    if hits:
        print(f"  {q:>4} [{c.get('scene','')[:22]:<22}] " + " | ".join(hits))
