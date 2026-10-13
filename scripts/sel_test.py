"""
PRUEBA DEFINITIVA de la sintaxis de seleccion de fixtures.

 store+export es la unica verificacion real (el Programmer no lista la
 seleccion). Se usan valores MUY distinguibles (R=11 G=22 B=33 DIM=44) para
 identificar sin ambiguedad que fixtures los recibieron.

Ademas contesta: si la seleccion sobrevive al Store, y si hace falta /merge
para agregar fixtures a un cue ya existente.

Escribe en la secuencia 156 (la de prueba), que se va a rehacer entera.
"""
import asyncio
import re
import sys
from xml.etree import ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")


def leer_export(nombre):
    """{fixture_id: {atributo: valor}} del cue 1 del xml exportado."""
    ruta = EXPORT_DIR / f"{nombre}.xml"
    if not ruta.exists():
        return None
    ns = {"m": "http://schemas.malighting.de/grandma2/xml/MA"}
    root = ET.parse(ruta).getroot()
    out = {}
    for cue in root.iter(f"{{{ns['m']}}}Cue"):
        for cd in cue.iter(f"{{{ns['m']}}}CueData"):
            ch = cd.find(f"{{{ns['m']}}}Channel")
            va = cd.find(f"{{{ns['m']}}}Value")
            if ch is None:
                continue
            fid = ch.get("fixture_id")
            attr = ch.get("attribute_name")
            val = va.text if va is not None else None
            out.setdefault(fid, {})[attr] = val
    return out


async def probar(ma2, etiqueta, seleccion):
    print("\n" + "=" * 78)
    print(f"PRUEBA: {etiqueta}")
    await ma2.cmd("cd /")
    r = await ma2.cmd(seleccion)
    print(f"  {seleccion:<28} prompt={r.prompt!r}"
          f"{'  ERR:' + str(r.errors) if r.errors else '  ok'}")
    if r.errors:
        return
    for c in ['Attribute "ColorRGB1" At 11',
              'Attribute "ColorRGB2" At 22',
              'Attribute "ColorRGB3" At 33',
              "At 44"]:
        rr = await ma2.cmd(c)
        if rr.errors:
            print(f"    {c}: ERR {rr.errors}")
            return
    r = await ma2.cmd("Store Cue 2 Sequence 156 /noconfirm /merge")
    print(f"  store -> errores={r.errors if r.errors else 'ninguno'}")
    r = await ma2.cmd('Export Sequence 156 "seltest"')
    print(f"  export -> errores={r.errors if r.errors else 'ninguno'}")

    datos = leer_export("seltest")
    if datos is None:
        print("  NO SE GENERO EL XML")
        return
    print(f"  fixtures con datos: {sorted(int(k) for k in datos)}")
    for fid in sorted(datos, key=int):
        print(f"     fx{fid}: {datos[fid]}")


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()!r}\n")
        # limpiar la secuencia 156 de la prueba anterior
        await ma2.cmd("cd /")
        for c in ["Clear Sequence 156", "Empty Sequence 156"]:
            r = await ma2.cmd(c)
            print(f"  {c:<24} prompt={r.prompt!r}"
                  f"{'  ERR:' + str(r.errors) if r.errors else '  ok'}")

        await probar(ma2, "rango con unidad en el primero", "Fixture 23.1 Thru 30")
        await probar(ma2, "rango sin unidad", "Fixture 23 Thru 30")
        await probar(ma2, "fixture suelto con unidad", "Fixture 15.1")


if __name__ == "__main__":
    asyncio.run(main())
