r"""
Reporte por cue para revisar antes del show: data/reporte_operador.md

Lee data/plan.json (que es lo que se grabo) y arma una tabla por escena con
los cinco grupos, marcando:
  - el efecto de cada celda (efN)
  - STROBO: las celdas donde ademas se puso Shutter PWM 6 ("stomps")
  - MULTI: celdas multicolor (varios colores base + arcoiris/barrido)
  - ⚠: celdas con algo para ajustar a mano (posicion, niveles relativos, etc.)

Uso: python scripts\reporte.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
SEQ_BASE = 155
BOTON = {1: "3.101", 2: "3.102", 3: "3.103", 4: "3.104", 5: "3.105", 6: "3.106"}
ORDEN = ["CM", "BT", "FRONT", "BM", "BF", "COB"]


def celda(gr, cg):
    if not cg or cg["accion"] == "nada":
        return "—"
    p = []
    if cg.get("dim") is not None:
        p.append(f"{cg['dim']}%")
    if cg.get("color"):
        p.append(cg["color"])
    if cg.get("alternar_rgb"):
        p.append("Cian/Dorado")
    ef = cg.get("efecto")
    if ef:
        real = 17 if (gr == "CM" and ef == 7) else ef
        p.append(f"ef{real}")
    b = (cg.get("bruto") or "").lower()
    if ("strob" in b or "stomp" in b) and "sin strob" not in b \
            and ef != 6:
        p.append("STROBO")
    if cg.get("multicolor"):
        p.append("MULTI")
    if cg.get("manual"):
        p.append("⚠")
    return " ".join(p) if p else "?"


def main():
    plan = json.loads((DATA / "plan.json").read_text(encoding="utf-8"))
    escenas = []
    for c in plan:
        if c["scene"] not in escenas:
            escenas.append(c["scene"])

    L = ["# Reporte por cue — fede inti y luna sep 2026", "",
         f"Grabado por Import ({len(plan)} cues en {len(escenas)} secuencias). Marcas:",
         "**efN** = efecto del pool N · **STROBO** = Shutter PWM 6 (stomp) · "
         "**MULTI** = multicolor · **⚠** = revisar a mano.",
         "En los cabezales (CM) el arcoiris/barrido de color del PDF se grabó "
         "como **ef17** (P/T Cross = barrido de haz), porque no tienen RGB.",
         "",
         "> En el grupo **BM** (fx15-22, Nebula Max 162) el ef6 no se puede "
         "escribir sobre SHUTTER: la consola descarta el cue y el strobo se "
         "pierde. Va sobre **DIM** y hace el mismo parpadeo "
         "(medido en `scripts/test_strobe_bm2.py`).", ""]

    tot_ef = tot_str = tot_multi = tot_manual = 0
    for i, esc in enumerate(escenas, 1):
        cues = [c for c in plan if c["scene"] == esc]
        L += [f"## Escena {i} — {esc.split('-', 1)[1].strip()}",
              f"Secuencia **{SEQ_BASE + i}** · botón **{BOTON[i]}** · "
              f"{len(cues)} cues", "",
              "| Cue | Momento | CM | BT | FRONT | BM | BF | COB |",
              "|---|---|---|---|---|---|---|---|"]
        for j, c in enumerate(cues, 1):
            g = c["grupos"]
            fila = [f"**{j}** ({c['cue']})", c.get("momento", "")]
            for gr in ORDEN:
                cg = g.get(gr)
                fila.append(celda(gr, cg))
                b = ((cg or {}).get("bruto") or "").lower()
                if cg and cg.get("efecto"):
                    tot_ef += 1
                if ("strob" in b or "stomp" in b) and "sin strob" not in b \
                        and cg and cg.get("efecto") != 6:
                    tot_str += 1
                if cg and cg.get("multicolor"):
                    tot_multi += 1
                if cg and cg.get("manual"):
                    tot_manual += 1
            L.append("| " + " | ".join(fila) + " |")
        L.append("")

    L.insert(5, f"Totales: {tot_ef} celdas con efecto, {tot_str} con STROBO "
                f"agregado, {tot_multi} multicolor, {tot_manual} con nota manual.")
    L.insert(6, "")

    # criterio de diseño, cita del guion
    L += ["---", "", "## Criterio por cue (por qué cada luz)", ""]
    for c in plan:
        L.append(f"**{c['cue']} — {c.get('momento', '')}**")
        L.append("")
        L.append(f"> {c.get('guion', '')}")
        L.append("")

    salida = DATA / "reporte_operador.md"
    salida.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"escrito {salida}")
    print(f"  {len(plan)} cues, {len(escenas)} escenas")
    print(f"  efecto={tot_ef}  STROBO={tot_str}  MULTI={tot_multi}  "
          f"manual={tot_manual}")


if __name__ == "__main__":
    main()
