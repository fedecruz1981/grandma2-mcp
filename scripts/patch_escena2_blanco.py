r"""
El operador: "la escena 2 no lleva color, borralle los colores, solo blanco".

Reglas aplicadas (piso lo que ya era blanco, como pidió):
  - Los blancos que YA estaban se respetan tal cual:
      Q7  blanco cálido  255/232/196
      Q9  blanco frío    214/232/255  (y CM blanco duro 255/255/255)
      Q10 blanco frío    214/232/255
      Q11 blanco duro    255/255/255
  - Todo lo que era color de verdad se pasa a blanco duro 255/255/255:
      gris neutro (Q9 BT), rojo oscuro (Q11 BT), y los grupos sin color
      anotado (Q6, Q8) que heredaban el color del cue anterior.
  - Los barridos/arcoíris (ef7 RGB Rainbow) se cambian por un efecto de
    INTENSIDAD (ef2 Dimmer Chase), para que la escena se mueva sin dar color.
    En los cabezales el ef7 ya no es color: se graba como ef17 (P/T Cross),
    que es barrido de haz, y se deja igual.

Edita data/plan.json. Uso: python scripts\patch_escena2_blanco.py
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sequences import ORDEN  # noqa: E402
from seqxml import CON_RGB  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
PLAN = DATA / "plan.json"

BLANCO_DURO = ("Blanco duro", [255, 255, 255])
EF_INTENSIDAD = 2          # Dimmer Chase


def es_blanco(nombre):
    return (nombre or "").startswith("Blanco")


def main():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    shutil.copy2(PLAN, PLAN.with_name(PLAN.name + ".bak_esc2blanco"))

    cambiados = {c["cue"]: [] for c in plan
                 if c["scene"].startswith("ESCENA 2 - ")}

    for c in plan:
        if not c["scene"].startswith("ESCENA 2 - "):
            continue
        for g in ORDEN:
            cg = c["grupos"].get(g)
            if not cg or cg.get("accion") == "nada":
                continue

            # ---- color: blanco
            if not es_blanco(cg.get("color")):
                antes = cg.get("color")
                cg["color"], cg["rgb"] = BLANCO_DURO
                cg.pop("alternar_rgb", None)
                cambiados[c["cue"]].append(
                    f"{g}: color {antes or '(sin color)'} -> Blanco duro")

            # ---- barrido de color -> efecto de intensidad
            if cg.get("efecto") == 7 and g in CON_RGB:
                cg["efecto"] = EF_INTENSIDAD
                cg["multicolor"] = False
                cambiados[c["cue"]].append(
                    f"{g}: ef7 RGB Rainbow -> ef2 Dimmer Chase")

            # ---- en los cabezales el ef7 ya no es color: se graba como ef17
            # (P/T Cross = barrido de haz). La marca multicolor solo alimenta el
            # reporte, asi que se saca para que no confunda.
            if cg.get("efecto") == 7:
                cg["multicolor"] = False
                cambiados[c["cue"]].append(f"{g}: (ef17 de haz, sin color)")

    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"backup: {PLAN.name}.bak_esc2blanco\n")
    for cue, cambios in cambiados.items():
        print(f"{cue}:")
        for x in cambios:
            print(f"    {x}")


if __name__ == "__main__":
    main()
