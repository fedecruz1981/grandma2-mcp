r"""
Parche de la escena 3: donde BT y BM quedaban en negro -> Cian 15%.

Pedido del operador: "nunca me dejes todo negro; en los LED pon algun cian
ya que debe contrastar con lo dorado de la mirada". Se aplica SOLO a la
escena 3, SOLO a BT y BM, y SOLO donde hoy estan en 0 (apagado).

Se edita data/plan.json (fuente de la que se regenera la secuencia 158) y se
deja un backup .bak_cian.

Uso: python scripts\patch_escena3_cian.py
"""
import json
import shutil
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
PLAN = DATA / "plan.json"
CIAN = [0, 255, 255]
ESCENA = "ESCENA 3 - "
NIVEL = 15


def main():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    shutil.copy2(PLAN, PLAN.with_name(PLAN.name + ".bak_cian"))

    cambios = []
    for c in plan:
        if not c.get("scene", "").startswith(ESCENA):
            continue
        for g in ("BT", "BM"):
            d = c["grupos"].get(g)
            if not d or d.get("dim") != 0:
                continue
            d["accion"] = "cambiar"
            d["dim"] = NIVEL
            d["color"] = "Cian"
            d["rgb"] = list(CIAN)
            d["efecto"] = None
            d["multicolor"] = False
            d["shutter"] = None
            d["bruto"] = (f"Cian {NIVEL}% (fondo de contraste con el dorado; "
                          "nunca negro)")
            d["manual"] = []
            d["avisos"] = []
            cambios.append(f'{c["cue"]} {g}')

    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print("backup:", PLAN.with_name(PLAN.name + ".bak_cian").name)
    print(f"cambios ({len(cambios)}): {cambios}")


if __name__ == "__main__":
    main()
