"""
¿Que atributos aceptan REALMENTE los cabezales fx1-4?

Hallazgo: al grabar la Escena 1, fx1-4 aceptaron DIM y SHUTTER pero NO
COLORRGB1/2/3. El verificador del grabador lo detecto (24 FALTAS, todas
COLORRGB de fx1-4). Los otros grupos (fx5-8, 9-14, 15-22, 23-30) guardaron
bien sus RGB.

Eso invalida la conclusion anterior de que "todos los fixtures tienen RGB",
que se apoyaba en `list attribute` -- y se vio que esa lista es UNIVERSAL
(41 atributos identicos para los 5 tipos), no por fixture.

Un Beamer 250 Mini probablemente tiene rueda de color y no RGB crudo, o el
perfil MA2 marca esos canales como no aplicables. Hay que ver cual de los dos.

Se prueban TODOS los atributos con pinta de servir para un cabezal, sobre la
secuencia 170 (tirada), y se mira cuales sobreviven en el export.

Uso: python scripts/cm_attr_test.py
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
SEQ = 170

# (atributo, valor) -- valores altos y distintos para ver quien sobrevive
PRUEBAS = [
    ("ColorRGB1", 11),
    ("ColorRGB2", 22),
    ("ColorRGB3", 33),
    ("Shutter", 44),
    ("Color1", 55),
    ("ColorTemperature", 66),
    ("Focus", 77),
    ("Gobo1", 88),
    ("Gobo1WheelSelectBlink", 99),
    ("Prisma1", 21),
    ("Frost", 43),
    ("DimmerCurve", 7),
    ("Zoom", 15),
    ("Beam", 12),
    ("Iris", 31),
]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {SEQ}")

        print("Clear primero, y los 15 atributos DESPUES, sin Clear en medio")
        await ma2.cmd("cd /")
        await ma2.cmd("Clear")
        for attr, val in PRUEBAS:
            await ma2.cmd("Fixture 1 Thru 4")
            r = await ma2.cmd(f'Attribute "{attr}" At {val}')
            marca = "" if not r.errors else "  <- RECHAZADO " + str(r.errors)
            print(f"  {attr:<24} At {val:<4} "
                  f"{'ok' if not r.errors else 'ERR'}{marca}")

        r = await ma2.cmd(f"Store Cue 1 Sequence {SEQ} /noconfirm")
        print(f"\nstore -> {'ok' if not r.errors else r.errors}")

        await ma2.cmd("cd /")
        await ma2.cmd(f'Export Sequence {SEQ} "cmattr"')
        ruta = EXPORT_DIR / "cmattr.xml"
        if not ruta.exists():
            print("no se genero xml")
            return
        root = ET.parse(ruta).getroot()
        print("\nlo que REALMENTE quedo guardado en fx1-4:")
        guardados = {}
        for cd in root.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            if ch is None:
                continue
            guardados.setdefault(ch.get("attribute_name"), set()).add(
                va.text if va is not None else None)
        for attr, _ in PRUEBAS:
            if attr in guardados:
                print(f"  {attr:<24} SI  valor={sorted(guardados[attr])}")
        otros = set(guardados) - {a for a, _ in PRUEBAS}
        if otros:
            print(f"  (otros guardados: {sorted(otros)})")

        print("\nRESUMEN")
        ok = [a for a, _ in PRUEBAS if a in guardados]
        no = [a for a, _ in PRUEBAS if a not in guardados]
        print(f"  ACEPTAN : {ok}")
        print(f"  RECHAZAN: {no}")

        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {SEQ}")
        print(f"\nsecuencia {SEQ} de prueba borrada")


if __name__ == "__main__":
    asyncio.run(main())