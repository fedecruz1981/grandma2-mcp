import json
from pathlib import Path
from collections import Counter
r = json.loads(Path("data/rig.json").read_text(encoding="utf-8"))
# dict indexado por id
for k in sorted(r, key=int)[:2]:
    print(f"--- fx{k} ---")
    print(json.dumps(r[k], ensure_ascii=False, indent=1))
print()
print("--- resumen ---")
c = Counter()
for k, f in r.items():
    c[(f.get("type"), f.get("name"), f.get("group"), f.get("layer"))] += 1
for kk, n in sorted(c.items(), key=lambda x: str(x[0])):
    print(f"  n={n:<3} type={str(kk[0]):<26} name={str(kk[1])[:38]:<38} grp={kk[2]} layer={kk[3]}")
