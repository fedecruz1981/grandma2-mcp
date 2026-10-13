"""
Lee la estructura Layer/Grupo de cada fixture via el prompt del telnet.

Truco: `cd Fixture N` deja el prompt en la ruta completa, que codifica la
organizacion del rig:

    LiveSetup/Layers 4/BEAM 3/BEAMER 250 MINI CCT 1 1 >
            ^layer    ^grupo 3   ^fixture type + id

Eso es lo unico del rig que esta en la consola; las posiciones 3D estan
todas en 0.00 porque el escenario 3D nunca se configuro.

Uso: python scripts/fixture_layers.py
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dotenv import load_dotenv

load_dotenv(HERE.parent / ".env")

from ma2_telnet import Ma2

OUT = HERE.parent / "data" / "rig.json"
LAYER_RE = re.compile(r"LiveSetup/Layers\s+(\S+)\s*/\s*(.*?)\s+(\d+)\s*/\s*(.+?)\s+(\d+)\s*$")


async def main():
    async with Ma2() as ma2:
        rig = {}
        for n in range(1, 40):
            r = await ma2.cmd(f"cd Fixture {n}")
            p = r.prompt
            # el prompt no siempre dice "Fixture": naming modules usan
            # "<FIXTURETYPE> <id> <unit>", ej. BEAMER 250 MINI CCT 1 1
            if "Error" in r.raw or "LiveSetup" not in p:
                continue
            m = LAYER_RE.search(p)
            if m:
                layer, group, gnum, ftype, fnum = m.groups()
                rig[n] = {"layer": layer, "group": group, "group_no": int(gnum),
                          "type": ftype, "unit": int(fnum)}
            else:
                rig[n] = {"raw_prompt": p}
            print(f"  fx{n:<3} {p}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rig, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(rig)} fixtures -> {OUT}")


if __name__ == "__main__":
    asyncio.run(main())