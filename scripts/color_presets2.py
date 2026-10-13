r"""
Rueda de color completa de los cabezales, leida del pool de presets.

`Export Preset 4 "pool"` falla (COMMAND NOT EXECUTED) pero `Export Preset 4.N`
individual funciona. Se exportan 4.1 .. 4.40 y de cada uno se saca el nombre y
el valor de COLOR1 en fx1-4 (mas COLORRGB para saber que colores son, porque
los presets probablemente cubren todo el rig).

Del show vivo ya se sabia: 0 White, 8 Yellow, 24 Blue, 32.5 Cyan.
Uso: python scripts\color_presets2.py
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
DESDE, HASTA = 1, 40


def leer(tag):
    ruta = EXPORT_DIR / f"{tag}.xml"
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    nombre = ""
    for p in root.iter(f"{NS}Preset"):
        nombre = p.get("name") or ""
    vals = {}
    for cd in root.iter(f"{NS}CueData"):
        ch = cd.find(f"{NS}Channel")
        va = cd.find(f"{NS}Value")
        if ch is None:
            continue
        fx = int(ch.get("fixture_id"))
        attr = ch.get("attribute_name")
        vals.setdefault(attr, {})[fx] = va.text if va is not None else None
    return nombre, vals


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        hallados = 0
        for n in range(DESDE, HASTA + 1):
            tag = f"cp_{n}"
            await ma2.cmd("cd /")
            r = await ma2.cmd(f'Export Preset 4.{n} "{tag}"')
            d = leer(tag)
            if d is None:
                continue
            nombre, vals = d
            hallados += 1
            col1 = vals.get("COLOR1", {})
            rgb = vals.get("COLORRGB1", {})
            c1 = sorted({v for f, v in col1.items() if f <= 4})
            c1todos = sorted({v for v in col1.values()})
            r1 = sorted({v for v in vals.get("COLORRGB1", {}).values()})
            g1 = sorted({v for v in vals.get("COLORRGB2", {}).values()})
            b1 = sorted({v for v in vals.get("COLORRGB3", {}).values()})
            ctc = sorted({v for v in vals.get("COLORTEMPERATURE", {}).values()})
            print(f"  4.{n:<2} {nombre!r:<22} "
                  f"COLOR1(cabezales)={c1[:5] if c1 else '-'} "
                  f"COLOR1(todos)={c1todos[:4] if c1todos else '-'} "
                  f"RGB={r1[:2]}/{g1[:2]}/{b1[:2]} "
                  f"CTC={ctc[:2]}")
        print(f"\n  presets con export: {hallados}")


if __name__ == "__main__":
    asyncio.run(main())
