"""
Depura por que cm_final.py da NO ENTRA hasta en el control (fx23-30).

cm_final.py y record_scene.py usan el MISMO patron de escritura
(Clear -> Fixture X Thru Y -> Attribute "ColorRGB1" At N -> At 55 ->
Store Cue 1 Sequence N /noconfirm). record_scene funciona; cm_final no.
La unica diferencia grande es que cm_final arranca con `Delete Sequence 190`
sobre una secuencia que no existe, que da error.

Este script hace UN caso (control fx23-30 -> seq 190) SIN el Delete, y
muestra la respuesta CRUDA de cada comando mas el archivo exportado, para
ver donde se corta la cadena.

Uso: python scripts\dbg_cm.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
SEQ = 190


async def ver(ma2, c):
    r = await ma2.cmd(c)
    estado = "ok" if not r.errors else "ERR " + str(r.errors)
    print(f">>> {c}")
    print(f"    [{estado}]  prompt={r.prompt!r}")
    for ln in [x for x in r.body if x.strip()][:6]:
        print(f"      {ln.strip()[:150]}")
    return r


async def main():
    xml = EXPORT_DIR / "dbgcm.xml"
    if xml.exists():
        xml.unlink()
        print(f"(borre el {xml.name} viejo para no leer basura)\n")

    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ver(ma2, "cd /")
        await ver(ma2, "Clear")
        await ver(ma2, "Fixture 23 Thru 30")
        await ver(ma2, 'Attribute "ColorRGB1" At 11')
        await ver(ma2, "At 55")
        await ver(ma2, f"Store Cue 1 Sequence {SEQ} /noconfirm")
        await ver(ma2, "cd /")
        await ver(ma2, f'Export Sequence {SEQ} "dbgcm"')

    print(f"\narchivo esperado: {xml}")
    print(f"existe: {xml.exists()}")
    if xml.exists():
        print(f"bytes : {xml.stat().st_size}")
        from xml.etree import ElementTree as ET
        NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
        root = ET.parse(xml).getroot()
        pares = []
        for cd in root.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            if ch is not None:
                pares.append((ch.get("fixture_id"),
                              ch.get("attribute_name"),
                              va.text if va is not None else None))
        print(f"CueData con Channel: {len(pares)}")
        for p in pares[:12]:
            print(f"   fx{p[0]:<4} {p[1]:<18} = {p[2]}")


if __name__ == "__main__":
    asyncio.run(main())
