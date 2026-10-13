r"""Lista las celdas del plan que mencionan strobo/stomp y que effect tienen.

El operador pidio: "every sequence containing effects must have its stomps
(strobe) afterwards". O sea el strobo no puede perderse. Esto revisa si el
traductor lo convirtio en effect 6 (Shutter PWM) o si lo tapo el barrido (7).

Uso: python scripts\_strobo.py
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
plan = json.loads((DATA / "plan.json").read_text(encoding="utf-8"))

print("celdas que mencionan strobo/stomp:")
n = 0
for c in plan:
    for g, cg in c["grupos"].items():
        b = (cg.get("bruto") or "").lower()
        if "strob" in b or "stomp" in b or "titil" in b or "parpade" in b:
            n += 1
            ef = cg.get("efecto")
            print(f"  {c['cue']:>4} {g:<5} efect={str(ef):<4} "
                  f"dim={str(cg.get('dim')):<5} {cg.get('bruto')}")
print(f"  ({n} celdas)")

print("\nceldas con effect 6 (Shutter PWM):")
for c in plan:
    for g, cg in c["grupos"].items():
        if cg.get("efecto") == 6:
            print(f"  {c['cue']:>4} {g:<5} shutter={cg.get('shutter')} "
                  f"{cg.get('bruto')}")

print("\nreparto de effects por grupo:")
from collections import Counter
cnt = Counter()
for c in plan:
    for g, cg in c["grupos"].items():
        if cg.get("efecto"):
            cnt[(g, cg["efecto"])] += 1
for (g, e), k in sorted(cnt.items()):
    print(f"  {g:<5} effect {e}: {k}")
