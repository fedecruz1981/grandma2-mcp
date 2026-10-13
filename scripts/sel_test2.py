"""
Busca una sintaxis de seleccion de fixtures que sea FIABLE.

Por que este script existe: `Fixture 23.1 Thru 30` no selecciono un rango
(solo fx23) y escribio basura `DIM='23.1'` en fx24-30. Un `Thru` mal
interpretado ensucia el show en silencio, asi que hay que encontrar una forma
que no pueda fallar asi, o resignarse a seleccionar fixture por fixture.

Candidates a probar, todos con valores unicos para poder identificarlos:
  Fixture 23.1 + 7        (offset relativo, sintaxis tipica de MA2)
  Fixture 23.1 Thru 30    (ya se que es dudoso, se repite controlado)
  Fixture 23.1            (unitario, control)
  At 23.1                (seleccion por At)

Cada prueba sobre una secuencia DISTINTA para que no se contaminen, y todas
verificadas por export (unico read-back fiable).
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

        # 1) limpiar la 156 a fondo
        await ma2.cmd("cd /")
        for c in ["Clear Sequence 156", "Delete Sequence 156"]:
            r = await ma2.cmd(c)
            print(f"  {c:<24} errores={r.errors if r.errors else 'ninguno'}")
        await ma2.cmd("cd /")
        await ma2.cmd('Export Sequence 156 "clean156"')
        d = leer("clean156")
        print(f"  156 tras limpiar: {d if d else '(vacia o inexistente)'}\n")

        PRUEBAS = [
            ("secuencia 160", "Fixture 23.1 + 7", 160),
            ("secuencia 161", "Fixture 23.1 Thru 30.1", 161),
            ("secuencia 162", "Fixture 23.1", 162),
            ("secuencia 163", "At 23.1", 163),
        ]

        for etiqueta, sel, seq in PRUEBAS:
            print("=" * 78)
            print(f"{etiqueta}: {sel!r}")
            await ma2.cmd("cd /")
            r = await ma2.cmd(sel)
            print(f"  seleccion -> prompt={r.prompt!r}  "
                  f"errores={r.errors if r.errors else 'ninguno'}")
            for c in ['Attribute "ColorRGB1" At 11',
                      'Attribute "ColorRGB2" At 22',
                      'Attribute "ColorRGB3" At 33',
                      "At 44"]:
                rr = await ma2.cmd(c)
                if rr.errors:
                    print(f"    {c} -> ERR {rr.errors}")
            r = await ma2.cmd(f"Store Cue 1 Sequence {seq} /noconfirm")
            print(f"  store -> errores={r.errors if r.errors else 'ninguno'}")
            await ma2.cmd("cd /")
            r = await ma2.cmd(f'Export Sequence {seq} "r{seq}"')
            d = leer(f"r{seq}")
            if d is None:
                print("  NO SE GENERO XML")
                continue
            print(f"  fixtures con datos: {sorted(int(k) for k in d)}")
            for fid in sorted(d, key=int):
                print(f"     fx{fid:>3}: {d[fid]}")


if __name__ == "__main__":
    asyncio.run(main())
