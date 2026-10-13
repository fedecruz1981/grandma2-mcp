"""
Diagnostico: por que el store no guarda nada en attr_matrix.py.

La escena 1 SI se grabo (DIM y SHUTTER quedaron en fx1-4), pero attr_matrix
reporta que NO se guarda nada, ni siquiera DIM. La diferencia entre ambos
scripts es el preambulo: attr_matrix hace `cd /` + `Delete Sequence` + `Clear`
antes de seleccionar.

Se corre el caso bueno (sin cd /, sin Delete, sin Clear) y el malo (con todo
el preambulo), mostrando la respuesta cruda de cada comando.

Uso: python scripts\diag_store.py
"""
import asyncio
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
SEQ = 190


def ver(tag):
    ruta = EXPORT_DIR / f"{tag}.xml"
    if not ruta.exists():
        return "SIN XML"
    root = ET.parse(ruta).getroot()
    vals = []
    for cd in root.iter(f"{NS}CueData"):
        ch = cd.find(f"{NS}Channel")
        va = cd.find(f"{NS}Value")
        if ch is not None:
            vals.append(f"fx{ch.get('fixture_id')}."
                        f"{ch.get('attribute_name')}="
                        f"{va.text if va is not None else '-'}")
    return f"{len(vals)} valores: {vals[:6]}" if vals else "CUE VACIO"


async def correr(ma2, etiqueta, cmds, tag):
    print("=" * 78)
    print(f"{etiqueta}")
    for c in cmds:
        r = await ma2.cmd(c)
        print(f"  {c:<44} {'ok' if not r.errors else 'ERR ' + str(r.errors)}")
    await ma2.cmd("cd /")
    r = await ma2.cmd(f'Export Sequence {SEQ} "{tag}"')
    print(f"  export -> {'ok' if not r.errors else r.errors}")
    print(f"  RESULTADO: {ver(tag)}")


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()!r}\n")

        # Caso A: el preambulo completo de attr_matrix
        await correr(ma2, "A) cd / + Delete + Clear + seleccionar + setear", [
            "cd /",
            f"Delete Sequence {SEQ}",
            "Clear",
            "Fixture 1 Thru 4",
            'Attribute "ColorRGB1" At 11',
            "At 55",
            f"Store Cue 1 Sequence {SEQ} /noconfirm",
        ], "diagA")

        # Caso B: sin Clear
        await correr(ma2, "B) sin Clear", [
            "cd /",
            f"Delete Sequence {SEQ}",
            "Fixture 1 Thru 4",
            'Attribute "ColorRGB1" At 11',
            "At 55",
            f"Store Cue 1 Sequence {SEQ} /noconfirm",
        ], "diagB")

        # Caso C: sin cd / ni Delete (solo Clear), como el grabador
        await correr(ma2, "C) Clear primero, sin cd / ni Delete", [
            "Clear",
            "Fixture 1 Thru 4",
            'Attribute "ColorRGB1" At 11',
            "At 55",
            f"Store Cue 1 Sequence {SEQ} /noconfirm",
        ], "diagC")

        # Caso D: con Clear DESPUES de seleccionar
        await correr(ma2, "D) seleccionar, luego Clear, luego setear", [
            "cd /",
            f"Delete Sequence {SEQ}",
            "Fixture 1 Thru 4",
            "Clear",
            'Attribute "ColorRGB1" At 11',
            "At 55",
            f"Store Cue 1 Sequence {SEQ} /noconfirm",
        ], "diagD")

        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {SEQ}")


if __name__ == "__main__":
    asyncio.run(main())