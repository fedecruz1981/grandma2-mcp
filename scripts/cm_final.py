"""
Confirma que fx1-4 (Beamer 250 Mini) no aceptan COLORRGB, y que si aceptan
que para dar color a los cabezales.

Contexto: la escena 1 se grabo y el verificador dio 24 FALTAS, todas
COLORRGB1/2/3 de fx1-4. Los otros grupos (fx5-8, 9-14, 15-22, 23-30)
guardaron sus RGB sin problema, asi que no es un problema del metodo sino del
fixture. Y `Attribute "Iris"/"Zoom"/"Beam"` dan OBJECT DOES NOT EXIST, o sea
que este cabezal no tiene iris: el unico control de haz es SHUTTER.

Ojo: NO mandar `Clear` entre la seleccion y el `Attribute`. En diag_store.py
caso D, Clear justo ahi movio la seleccion y el ColorRGB1 fue a parar a fx5-10
en vez de fx1-4. Patron seguro: Clear, seleccionar, atributos, At, Store.

Se usa fx23-30 como CONTROL: si ahi ColorRGB1 entra, el metodo anda.

Uso: python scripts\cm_final.py
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
SEQ = 190

CASOS = [
    ("CONTROL  fx23-30", 23, 30, "ColorRGB1", 11),
    ("CONTROL  fx23-30", 23, 30, "ColorRGB2", 22),
    ("CONTROL  fx23-30", 23, 30, "ColorRGB3", 33),
    ("CM        fx1-4",   1, 4,   "ColorRGB1", 11),
    ("CM        fx1-4",   1, 4,   "Color1", 55),
    ("CM        fx1-4",   1, 4,   "ColorTemperature", 66),
    ("CM        fx1-4",   1, 4,   "Shutter", 44),
    ("CM        fx1-4",   1, 4,   "Focus", 77),
    ("CM        fx1-4",   1, 4,   "Pan", 50),
    ("CM        fx1-4",   1, 4,   "Tilt", 50),
    ("CONTROL  fx5-8",    5, 8,   "ColorRGB1", 11),
]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for etiqueta, ini, fin, attr, val in CASOS:
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {SEQ}")
            await ma2.cmd("Clear")
            sel = (f"Fixture {ini}" if ini == fin
                   else f"Fixture {ini} Thru {fin}")
            await ma2.cmd(sel)
            r = await ma2.cmd(f'Attribute "{attr}" At {val}')
            await ma2.cmd("At 55")
            await ma2.cmd(f"Store Cue 1 Sequence {SEQ} /noconfirm")
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {SEQ} "cmf"')
            ruta = EXPORT_DIR / "cmf.xml"
            vals = {}
            if ruta.exists():
                root = ET.parse(ruta).getroot()
                for cd in root.iter(f"{NS}CueData"):
                    ch = cd.find(f"{NS}Channel")
                    va = cd.find(f"{NS}Value")
                    if ch is not None:
                        vals.setdefault(ch.get("attribute_name"), set()).add(
                            va.text if va is not None else None)
            ok = attr in vals
            print(f"  {'ENTRA ' if ok else 'NO ENTRA'}  {etiqueta:<18} "
                  f"{attr:<18} {sorted(vals.get(attr, []))}"
                  f"{'   ERR: ' + str(r.errors) if r.errors else ''}")

        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {SEQ}")


if __name__ == "__main__":
    asyncio.run(main())