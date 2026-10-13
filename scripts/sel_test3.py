"""
Ultimo intento de conseguir un rango de fixtures que funcione.

Motivacion: seleccionar fixture por fixture son 5 comandos por fixture
(1 seleccion + 4 atributos). Con 22 fixtures x 53 cues son ~5900 comandos
(~13 min a 130 ms). Un rango correcto lo bajaria a ~110 por cue.

Ya se que NO funciona:
  Fixture 23.1 Thru 30.1   -> ILLEGAL RANGE
  Fixture 23.1 Thru 30     -> selecciona solo 23 + escribe basura
  Fixture 23.1 + 7         -> selecciona 23 y 7

Formas a probar:
  At 23.1 Thru 30.1
  Fixture 23.1 Thru Fixture 30.1
  23.1 Thru 30.1
  At 23 Thru 30

Si ninguna funciona, se usa fixture por fixture: es lo unico que el export
demostro que es exacto.
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


def leer(nombre):
    ruta = EXPORT_DIR / f"{nombre}.xml"
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    out = {}
    for cd in root.iter(f"{NS}CueData"):
        ch = cd.find(f"{NS}Channel")
        va = cd.find(f"{NS}Value")
        if ch is None:
            continue
        out.setdefault(ch.get("fixture_id"), {})[ch.get("attribute_name")] = (
            va.text if va is not None else None)
    return out


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()!r}\n")
        FORMAS = [
            "At 23.1 Thru 30.1",
            "Fixture 23.1 Thru Fixture 30.1",
            "23.1 Thru 30.1",
            "At 23 Thru 30",
            "Fixture 23 Thru 30",
        ]
        for i, sel in enumerate(FORMAS):
            seq = 170 + i
            print("=" * 78)
            print(f"{sel!r}  -> secuencia {seq}")
            await ma2.cmd("cd /")
            # limpiar la seleccion previa: seleccionar uno solo y luego el rango
            await ma2.cmd("Fixture 1.1")
            r = await ma2.cmd(sel)
            print(f"  -> prompt={r.prompt!r}  "
                  f"errores={r.errors if r.errors else 'ninguno'}")
            for c in ['Attribute "ColorRGB1" At 11',
                      'Attribute "ColorRGB2" At 22',
                      'Attribute "ColorRGB3" At 33',
                      "At 44"]:
                await ma2.cmd(c)
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"Store Cue 1 Sequence {seq} /noconfirm")
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "q{seq}"')
            d = leer(f"q{seq}")
            if d is None:
                print("  sin XML")
                continue
            fxs = sorted(int(k) for k in d)
            print(f"  fixtures con datos: {fxs}")
            muestra = {k: d[k] for k in list(d)[:2]}
            print(f"  muestra: {muestra}")
            if fxs == list(range(23, 31)):
                print("  *** RANGO CORRECTO 23..30 ***")
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {seq}")


if __name__ == "__main__":
    asyncio.run(main())
