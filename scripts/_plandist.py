import json, collections
from pathlib import Path
plan = json.loads(Path("data/plan.json").read_text(encoding="utf-8"))
por_grupo = collections.Counter()
detalle = collections.defaultdict(list)
for f in plan:
    for g, r in f["grupos"].items():
        if r.get("efecto"):
            por_grupo[(g, r["efecto"])] += 1
            detalle[(g, r["efecto"])].append(f["cue"])
print("effect por grupo (grupo, id) -> n cues:", dict(por_grupo))
print()
for (g, e), cues in sorted(detalle.items()):
    print(f"  {g:<6} effect {e:<2}  {len(cues):>2} cues: {cues}")
print()
tot = sum(1 for f in plan if any(r.get('efecto') for r in f['grupos'].values()))
multi = [f['cue'] for f in plan if any(r.get('multicolor') for r in f['grupos'].values())]
print("cues con effect:", tot, "| multicolor:", multi)
