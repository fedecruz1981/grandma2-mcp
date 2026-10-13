"""
Lee el contenido REAL de los presets que usa un cue.

Sec 137 'malvado' referencia Dimmer 1.1 'dim frente' y Dimmer 1.2 'STR back'.
Los tiempos del cue dan FADE_COLOR=0, asi que el color (si hay) tiene que
estar DENTRO del preset. Este script baja a cada preset y lee sus valores.

Sintaxis de preset en MA2: Preset <tipo> <pool>.<slot>  -- pool 1-9
  1 Dimmer   2 Position  3 Beam   4 Gobo   5 Color   6 Control
  7 Lenses   8 Effects   9 Other

Uso: python scripts/inspect_preset.py [preset_type] [slot]
"""
import asyncio
import re
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])

from ma2_telnet import Ma2

PRESET_NAMES = {
    1: "Dimmer", 2: "Position", 3: "Beam", 4: "Gobo", 5: "Color",
    6: "Control", 7: "Lenses", 8: "Effects", 9: "Other",
}


async def main():
    ptype = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    slot = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    async with Ma2() as ma2:
        # ir al pool de presets del tipo pedido
        nav = await ma2.cmd(f"cd Preset {ptype}")
        print(f"prompt tras cd Preset {ptype}: {nav.prompt}")

        r = await ma2.cmd("list")
        print(f"\n--- pool {PRESET_NAMES.get(ptype, '?')} ---")
        for ln in r.body:
            print("   ", ln)

        # entrar al preset concreto
        nav = await ma2.cmd(f"cd Preset {ptype}.{slot}")
        print(f"\nprompt: {nav.prompt}")

        for sub in ("", "values", "attribute", "fixture", "group"):
            cmd = f"list {sub}".strip()
            rr = await ma2.cmd(cmd)
            body = [ln for ln in rr.body if ln.strip()]
            if body:
                print(f"\n--- list {sub or '(raiz)'} ---")
                for ln in body[:40]:
                    print("   ", ln)
            if "Cue" not in nav.prompt and sub == "":
                break


if __name__ == "__main__":
    asyncio.run(main())