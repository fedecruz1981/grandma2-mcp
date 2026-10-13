"""
Informe legible de data/cues.json (lo que exportó sweep_sequences.py).

Muestra por secuencia: nombre, nº de cues, fixtures que toca, atributos
usados, presets de color referenciados y tiempos de fade/delay.

Uso:
  python scripts/cue_report.py              # resumen de todo
  python scripts/cue_report.py 137          # detalle de una secuencia
  python scripts/cue_report.py --colors     # quien usa cada preset de color
  python scripts/cue_report.py --blank      # secuencias sin ningun fixture
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data" / "cues.json"

ATTR_SHORT = {
    "PAN": "pan", "TILT": "tilt", "COLOR1": "color",
    "DIMMER": "dim", "BEAM": "beam", "GOBO": "gobo",
    "CONTROL": "ctrl", "FOCUS": "focus", "ZOOM": "zoom",
    "SHUTTER": "shutter", "XYZ": "xyz",
}


def load():
    """Carga cues.json y normaliza: claves de secuencia y de fixture a int."""
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    out = {}
    for k, v in raw.items():
        for c in v["cues"]:
            c["fixtures"] = {int(f): a for f, a in c["fixtures"].items()}
        out[int(k)] = v
    return out


def fixture_types(ma2_fix: dict) -> dict:
    return ma2_fix  # patch conocido, se inyecta abajo si hace falta


# patch conocido del show (leido de `list fixture`)
PATCH = {}
for i in range(1, 5):
    PATCH[i] = ("Beamer 250 Mini CCT", 15)
for i in range(5, 9):
    PATCH[i] = ("Stromber CCT", 15)
for i in range(9, 15):
    PATCH[i] = ("Nebula Flat 210 CCT", 8)
for i in range(15, 23):
    PATCH[i] = ("Nebula Max 162 CCT", 5)
for i in range(23, 31):
    PATCH[i] = ("Protone LED Frente", 2)
PATCH[31] = ("Blinder", 9)
for i in range(32, 35):
    PATCH[i] = ("Par COB II", 2)
CH = {31: "1.312", **{i: f"2.{100+i*1}" for i in range(23, 31)}}


def cue_line(cue: dict, verbose=False) -> str:
    """Una linea por cue con los fixtures y sus atributos."""
    fx = cue["fixtures"]
    if not fx:
        return "(solo tiempos)"
    bits = []
    for fid in sorted(fx):
        attrs = fx[fid]
        name = PATCH.get(fid, ("?", 0))[0]
        if not verbose:
            marks = []
            for a, d in attrs.items():
                v = d.get("value")
                p = d.get("preset")
                if p:
                    marks.append(f"{ATTR_SHORT.get(a, a)}={p}")
                elif a in ("PAN", "TILT") and v:
                    marks.append(f"{ATTR_SHORT.get(a, a)}={float(v):.0f}")
                elif a == "DIMMER" and v:
                    marks.append(f"dim={float(v):.0f}")
            if marks:
                bits.append(f"fx{fid}: " + " ".join(marks))
            else:
                bits.append(f"fx{fid}: ({', '.join(attrs)})")
        else:
            parts = []
            for a, d in attrs.items():
                s = f"{a}={d.get('value')}"
                if d.get("preset"):
                    s += f" [{d['preset']}]"
                parts.append(s)
            bits.append(f"fx{fid}: " + ", ".join(parts))
    return "\n        ".join(bits)


def main():
    data = load()
    args = sys.argv[1:]

    if args and args[0] == "--fixtures":
        from collections import Counter, defaultdict

        uses = Counter()
        seqs = defaultdict(set)
        colors = defaultdict(Counter)
        for s, d in data.items():
            for c in d["cues"]:
                for f, attrs in c["fixtures"].items():
                    uses[f] += 1
                    seqs[f].add(s)
                    for a, v in attrs.items():
                        if v.get("preset"):
                            colors[f][v["preset"]] += 1
        print(f"{'fx':>4}  {'tipo':<22} {'cues':>5} {'secs':>5}  color / preset mas usado")
        print("-" * 92)
        for f in sorted(uses):
            name = PATCH.get(f, ("?", 0))[0]
            top = colors[f].most_common(3)
            tops = ", ".join(f"{p}×{c}" for p, c in top) if top else "(solo posicion)"
            print(
                f"{f:>4}  {name:<22} {uses[f]:>5} {len(seqs[f]):>5}  {tops}"
            )
        print("-" * 92)
        print(f"{len(uses)} fixtures en uso | {sum(uses.values())} tocados-cue")
        return

    if args and args[0] == "--colors":
        usage = defaultdict(set)
        for n, d in data.items():
            for c in d["cues"]:
                for fid, attrs in c["fixtures"].items():
                    for a, v in attrs.items():
                        if v.get("preset"):
                            usage[v["preset"]].add(n)
        print(f"{len(usage)} presets de color referenciados\n")
        for p, seqs in sorted(usage.items(), key=lambda kv: -len(kv[1])):
            s = sorted(seqs)
            print(f"  {p:<22} {len(s):>3} cues  seq {s[:12]}{'...' if len(s)>12 else ''}")
        return

    if args and args[0] == "--blank":
        blank = [n for n, d in data.items() if not d["cues"]]
        print(f"{len(blank)} secuencias sin contenido:")
        for n in blank:
            print(f"  {n:>4}  {data[n]['name']}")
        return

    if args:
        n = int(args[0])
        d = data[n]
        print(f"SEQ {n}  '{d['name']}'   appearance={d['appearance']}")
        print(f"  {len(d['cues'])} cue(s)\n")
        for c in d["cues"]:
            t = c["timings"]
            tsum = " ".join(f"{k}:{v}" for k, v in sorted(t.items())) or "sin tiempos"
            print(f"  CUE {c['cue']}  [{tsum}]")
            print("        " + cue_line(c, verbose=("-v" in args)))
        return

    # resumen general
    print(f"{'SEQ':>5}  {'CUES':>4}  {'FIXTURES':>8}  NOMBRE / CONTENIDO")
    print("-" * 100)
    total_fx = set()
    for n in sorted(data):
        d = data[n]
        cues = d["cues"]
        if not cues:
            print(f"{n:>5}  {'-':>4}  {'-':>8}  {d['name']}   (vacio)")
            continue
        fxs = sorted({f for c in cues for f in c["fixtures"]})
        total_fx.update(fxs)
        first = cue_line(cues[0]).split("\n")[0]
        extra = f" +{len(cues)-1}" if len(cues) > 1 else ""
        print(f"{n:>5}  {len(cues):>4}{extra:<3} {len(fxs):>8}  {d['name']}")
        print(f"{'':>21}{first[:78]}")
    print("-" * 100)
    print(f"fixtures distintos usados en todo el show: {len(total_fx)} -> {sorted(total_fx)}")


if __name__ == "__main__":
    main()