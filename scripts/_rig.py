import json, sys
from pathlib import Path
r = json.loads(Path("data/rig.json").read_text(encoding="utf-8"))
print("tipo del dump:", type(r).__name__)
if isinstance(r, dict):
    print("claves:", list(r.keys())[:20])
    fx = r.get("fixtures", r)
else:
    fx = r
if isinstance(fx, list):
    print("total fixtures:", len(fx))
    print("--- campos de un fixture ---")
    print(json.dumps(fx[0], ensure_ascii=False, indent=1))
    print("--- resumen por tipo ---")
    from collections import Counter
    c = Counter()
    for f in fx:
        c[(f.get("id"), f.get("type"), f.get("name"), f.get("group"))] += 1
    for k in sorted(c, key=lambda x: (x[0] or 0)):
        print(f"  fx{k[0]:<3} {str(k[1]):<26} {str(k[2])[:34]:<34} grp={k[3]}")
