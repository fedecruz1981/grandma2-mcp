r"""
Lista, cue por cue, lo que quedo grabado en una escena.

Lee data/plan.json (fuente de verdad de lo grabado) y muestra por grupo:
accion, DIM, color (rueda COLOR1 en CM / RGB en el resto), efecto, shutter,
multicolor, snap/duracion y las notas manuales.

Uso: python scripts\listar_escena.py [n]      (n = 3 por defecto)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seqxml import EFECTOS, RUEDA, pct  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
PLAN = json.loads((DATA / "plan.json").read_text(encoding="utf-8"))

GRUPOS = ["CM", "BT", "FRONT", "BM", "BF"]


def linea(grupo, d):
    partes = [f"**{grupo}**"]
    if d["accion"] == "nada":
        partes.append("sin cambio (mantiene lo anterior)")
    elif d["accion"] == "derivado":
        partes.append("derivado del PDF")
    if d["dim"] is not None:
        partes.append(f"DIM {d['dim']}%")
    if d["color"]:
        if grupo == "CM":
            r = RUEDA.get(d["color"])
            partes.append(f"{d['color']} (rueda COLOR1 = {r})")
        else:
            partes.append(d["color"])
    if grupo != "CM" and d.get("rgb"):
        partes.append("RGB " + "/".join(f"{pct(v)}" for v in d["rgb"]))
    if d["efecto"]:
        nom = EFECTOS.get(d["efecto"], (f"ef{d['efecto']}",))[0]
        if grupo == "CM" and d["efecto"] == 7:
            partes.append("ef7->**ef17** P/T Cross (barrido de haz)")
        else:
            partes.append(f"**ef{d['efecto']}** ({nom})")
    if d["shutter"] is not None:
        estado = "abierto" if d["shutter"] == 0 else ("cerrado" if d["shutter"] == 100
                                                      else str(d["shutter"]))
        partes.append(f"SHUTTER {d['shutter']} ({estado})")
    if d["multicolor"]:
        partes.append("MULTI")
    if d["snap"]:
        partes.append("snap (fade 0)")
    if d["segundos"] is not None:
        partes.append(f"{d['segundos']} s")
    return " · ".join(partes)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    cues = [c for c in PLAN if f"ESCENA {n} - " in c.get("scene", "")]
    if not cues:
        print(f"no encontre la escena {n}")
        return
    print(f"# Escena {n}: {cues[0]['scene']}  ({len(cues)} cues)\n")
    for c in cues:
        print(f"### {c['cue']} — {c['momento']}")
        cols = []
        for g in GRUPOS:
            d = c["grupos"].get(g)
            if not d:
                continue
            if d["accion"] == "nada" and not any(
                    d.get(k) for k in ("dim", "color", "efecto", "shutter", "bruto")):
                continue
            cols.append(linea(g, d))
        for ln in cols:
            print(f"- {ln}")
        for m in c.get("manual", []):
            print(f"  - ⚠ {m}")
        print()


if __name__ == "__main__":
    main()
