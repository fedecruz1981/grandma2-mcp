r"""
Pedido del operador:

  1) "los cob frontales de arriba de la cabina" (Par COB II, fx32-34) al 50%
     en TODOS los cues de la escena 1 y de la escena 3.
  2) Escena 3: en las barras BT y BM, intercalar cian y dorado fixture por
     fixture ("por fixture en las barras") y mas intenso (15% -> 50%).

Edita data/plan.json (fuente de la que se regeneran las secuencias 156 y 158)
y deja un backup .bak_cob.

Uso: python scripts\patch_cob_y_escena3.py
"""
import json
import shutil
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
PLAN = DATA / "plan.json"

CIAN = [0, 255, 255]
DORADO = [255, 190, 60]        # palette.md -> "Dorado"
NIVEL = 50

COB = {
    "accion": "cambiar",
    "dim": NIVEL,
    "color": None,
    "rgb": None,
    "efecto": None,
    "multicolor": False,
    "shutter": None,
    "snap": False,
    "segundos": None,
    "manual": [],
    "avisos": [],
    "bruto": f"Par COB frontal (sobre la cabina) al {NIVEL}%",
}


def main():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    shutil.copy2(PLAN, PLAN.with_name(PLAN.name + ".bak_cob"))

    cob_n = 0
    alt_n = 0
    for c in plan:
        esc = c.get("scene", "")
        if esc.startswith("ESCENA 1 - ") or esc.startswith("ESCENA 3 - "):
            c["grupos"]["COB"] = dict(COB)
            cob_n += 1
        if esc.startswith("ESCENA 3 - "):
            for g in ("BT", "BM"):
                d = c["grupos"].get(g)
                if not d:
                    continue
                d["accion"] = "cambiar"
                d["dim"] = NIVEL
                d["color"] = None
                d["rgb"] = None
                d["alternar_rgb"] = [list(CIAN), list(DORADO)]
                d["efecto"] = None
                d["multicolor"] = False
                d["shutter"] = None
                d["bruto"] = (f"Intercalado cian/dorado {NIVEL}% "
                              "(fixture por fixture)")
                d["manual"] = []
                d["avisos"] = []
                alt_n += 1

    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"backup: {PLAN.name}.bak_cob")
    print(f"cues con COB al {NIVEL}%: {cob_n}")
    print(f"grupos BT/BM intercalados: {alt_n}")


if __name__ == "__main__":
    main()
