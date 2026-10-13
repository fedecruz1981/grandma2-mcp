r"""
Intenta sacar la rueda de color completa de los cabezales desde los presets.

fx1-4 solo tienen COLOR1 (rueda). Del show vivo se saben 4 posiciones:
  0 White, 8 Yellow, 24 Blue, 32.5 Cyan
Faltan rojo, naranja, rosa, morado, dorado, blanco calido, etc.

Dos intentos, ambos por telnet:
  1. `list preset 4`  -> nombres de los presets de color
  2. `Export Preset 4 "cpres"` -> si la consola exporta el pool, se leen los
     valores de COLOR1 de los cabezales por preset
Uso: python scripts\color_presets.py
"""
import asyncio
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()

        print("=" * 78)
        print("1) nombres de los presets de color")
        for forma in ("list preset 4", "cd Presets", "list"):
            await ma2.cmd("cd /")
            r = await ma2.cmd(forma)
            print(f">>> {forma}   [{'ok' if not r.errors else 'ERR'}]")
            for ln in [x for x in r.body if x.strip()][:40]:
                print(f"      {ln.strip()[:130]}")

        print()
        print("=" * 78)
        print("2) export del pool de presets de color")
        for forma in ('Export Preset 4 "cpres"',
                      'Export Preset 4.1 "cpres1"'):
            await ma2.cmd("cd /")
            r = await ma2.cmd(forma)
            print(f">>> {forma}   [{'ok' if not r.errors else 'ERR ' + str(r.errors)}]")
            for ln in [x for x in r.body if x.strip()][:3]:
                print(f"      {ln.strip()[:130]}")

        for f in ("cpres.xml", "cpres1.xml"):
            ruta = EXPORT_DIR / f
            print(f"\n  {f}: existe={ruta.exists()}"
                  f"{'  ' + str(ruta.stat().st_size) + ' bytes' if ruta.exists() else ''}")

        ruta = EXPORT_DIR / "cpres.xml"
        if ruta.exists():
            root = ET.parse(ruta).getroot()
            print("\n  presets y valores de fx1-4:")
            for pr in root.iter(f"{NS}Preset"):
                # busca presets en el arbol
                pass
            for cd in root.iter(f"{NS}CueData"):
                ch = cd.find(f"{NS}Channel")
                va = cd.find(f"{NS}Value")
                if ch is None or int(ch.get("fixture_id")) > 4:
                    continue
                print(f"    fx{ch.get('fixture_id')} "
                      f"{ch.get('attribute_name')} = "
                      f"{va.text if va is not None else None}")


if __name__ == "__main__":
    asyncio.run(main())
