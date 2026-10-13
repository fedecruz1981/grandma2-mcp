r"""
Correccion de los COB pedida por el operador:

  - "los cob no daban color": su color soportado es "CALIDO" (preset 4.18),
    que en el tipo PAR COB II se guarda como COLORRGB18=100 + COLORRGB5=0
    (NO en RGB1/2/3). Comprobado exportando el preset real.
  - Bajarlos a 40%.
  - Dejarlos en TODAS las escenas menos la 2.

Edita data/plan.json. Uso: python scripts\patch_cob_calido40.py
"""
import copy
import json
import shutil
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
PLAN = DATA / "plan.json"

NIVEL = 40
ATTRS = {"COLORRGB18": 100, "COLORRGB5": 0}
CON_COB = ("ESCENA 1 - ", "ESCENA 3 - ",
           "ESCENA 4 - ", "ESCENA 5 - ", "ESCENA 6 - ")

COB = {
    "accion": "cambiar",
    "dim": NIVEL,
    "color": "Cálido",
    "rgb": None,
    "efecto": None,
    "multicolor": False,
    "shutter": None,
    "snap": False,
    "segundos": None,
    "manual": [],
    "avisos": [],
    "attrs": dict(ATTRS),
    "bruto": f"Par COB frontal al {NIVEL}% en Cálido (COLORRGB18/5)",
}


def main():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    shutil.copy2(PLAN, PLAN.with_name(PLAN.name + ".bak_calido40"))

    puestos = 0
    quitados = []
    for c in plan:
        esc = c.get("scene", "")
        if esc.startswith(CON_COB):
            c["grupos"]["COB"] = copy.deepcopy(COB)
            puestos += 1
        elif "COB" in c["grupos"]:
            del c["grupos"]["COB"]
            quitados.append(c["cue"])

    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"backup: {PLAN.name}.bak_calido40")
    print(f"cues con COB al {NIVEL}% calido: {puestos}")
    print(f"cues sin COB: {quitados}")


if __name__ == "__main__":
    main()
