"""
Analiza PAN/TILT por fixture en todos los cues.

Los 4 Beamer 250 son moviles, asi que cada cue guarda la punteria real.
Sirve para dos cosas:
  1. Verificar la descripcion fisica del usuario (barra atras, centro, etc.)
  2. Etiquetar el diagrama con la punteria que usa cada cue

Tambien lista los presets de Position referenciados, que son punterias
guardadas con nombre (ej. "Position 2.1").

Uso: python scripts/aiming.py [fixture_id]
"""
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data" / "cues.json"

PATCH = {}
for rng, name in [
    (range(1, 5), "Beamer 250 Mini CCT"),
    (range(5, 9), "Stromber CCT"),
    (range(9, 15), "Nebula Flat 210 CCT"),
    (range(15, 23), "Nebula Max 162 CCT"),
    (range(23, 31), "Protone LED Frente"),
    ([31], "Blinder"),
    (range(32, 35), "Par COB II"),
]:
    for f in rng:
        PATCH[f] = name


def load():
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    out = {}
    for k, v in raw.items():
        for c in v["cues"]:
            c["fixtures"] = {int(f): a for f, a in c["fixtures"].items()}
        out[int(k)] = v
    return out


def main():
    data = load()
    args = sys.argv[1:]
    only = int(args[0]) if args and args[0].isdigit() else None

    # pan/tilt numerico por fixture, y presets de posicion por fixture
    pan = defaultdict(list)
    tilt = defaultdict(list)
    pos_presets = defaultdict(Counter)
    seqs_with = defaultdict(set)
    touched = defaultdict(set)

    for n, d in data.items():
        for c in d["cues"]:
            for f, attrs in c["fixtures"].items():
                touched[f].add(n)
                for a, v in attrs.items():
                    num = v.get("value") not in (None, "")
                    if a == "PAN" and num and not v.get("preset"):
                        pan[f].append(float(v["value"]))
                    elif a == "TILT" and num and not v.get("preset"):
                        tilt[f].append(float(v["value"]))
                    elif a in ("PAN", "TILT") and v.get("preset"):
                        pos_presets[f][v["preset"]] += 1
                    if a in ("PAN", "TILT"):
                        seqs_with[f].add(n)

    print("=" * 78)
    print("PUNTERIA REAL POR FIXTURE (de los cues)")
    print("=" * 78)
    for f in sorted(PATCH):
        p, t = pan.get(f, []), tilt.get(f, [])
        ps = pos_presets.get(f)
        name = PATCH[f]
        print(f"\nfx{f:<3} {name}")
        if p:
            print(f"      pan  n={len(p):<4} min={min(p):7.1f}  max={max(p):7.1f}  "
                  f"media={statistics.mean(p):7.1f}")
        if t:
            print(f"      tilt n={len(t):<4} min={min(t):7.1f}  max={max(t):7.1f}  "
                  f"media={statistics.mean(t):7.1f}")
        if ps:
            top = ", ".join(f"{k}×{v}" for k, v in ps.most_common(4))
            print(f"      presets de posicion: {top}")
        if not p and not t:
            print(f"      fixture fijo (sin pan/tilt) — "
                  f"{len(touched[f])} secuencias lo tocan")

    if only:
        print(f"\n\n=== DETALLE fx{only}: pan/tilt por cue ===")
        rows = []
        for n in sorted(data):
            for c in data[n]["cues"]:
                a = c["fixtures"].get(only)
                if not a:
                    continue
                pv = a.get("PAN", {})
                tv = a.get("TILT", {})
                pn = pv.get("preset") or (f"{float(pv['value']):.1f}" if pv.get("value") else "-")
                tn = tv.get("preset") or (f"{float(tv['value']):.1f}" if tv.get("value") else "-")
                rows.append((n, data[n]["name"], c["cue"], pn, tn))
        for n, nm, cn, pn, tn in rows:
            print(f"  seq {n:<4} cue {cn:<3} {nm[:26]:<26} pan={pn:<14} tilt={tn}")


if __name__ == "__main__":
    main()