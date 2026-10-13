"""
Enumera, atributo por atributo, que acepta de verdad cada grupo de fixtures.

Por que: dos pruebas anteriores se contradijeron porque reemitian
`Fixture 1 Thru 4` antes de cada atributo, y eso parece BORRAR los valores
pendientes del programador. Con un solo atributo por store no hay ambiguedad.

Metodo: para cada (grupo, atributo) se borra la secuencia 170, se selecciona
el grupo, se setea UN atributo, se guarda y se exporta. Si aparece en el XML,
el fixture lo acepta de verdad.

Ademas imprime el valor de DIM que queda, para no seguir Suponiendo.

Uso: python scripts/attr_matrix.py
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

GRUPOS = {
    "CM fx1-4":    (1, 4),
    "BT fx5-8":    (5, 8),
    "FRONT fx9-14": (9, 14),
    "BM fx15-22":  (15, 22),
    "BF fx23-30":  (23, 30),
}

ATRIBUTOS = [
    ("ColorRGB1", 11),
    ("ColorRGB2", 22),
    ("ColorRGB3", 33),
    ("Shutter", 44),
    ("Color1", 55),
    ("ColorTemperature", 66),
    ("Focus", 77),
    ("Pan", 50),
    ("Tilt", 50),
]


async def guardar(ma2, ini, fin, attr, val):
    await ma2.cmd("cd /")
    await ma2.cmd(f"Delete Sequence {SEQ}")
    await ma2.cmd("Clear")
    sel = f"Fixture {ini}" if ini == fin else f"Fixture {ini} Thru {fin}"
    await ma2.cmd(sel)
    r = await ma2.cmd(f'Attribute "{attr}" At {val}')
    err = r.errors
    await ma2.cmd(f"Store Cue 1 Sequence {SEQ} /noconfirm")
    await ma2.cmd("cd /")
    await ma2.cmd(f'Export Sequence {SEQ} "mat"')
    ruta = EXPORT_DIR / "mat.xml"
    if not ruta.exists():
        return None, "sin xml"
    root = ET.parse(ruta).getroot()
    out = {}
    for cd in root.iter(f"{NS}CueData"):
        ch = cd.find(f"{NS}Channel")
        va = cd.find(f"{NS}Value")
        if ch is None:
            continue
        out.setdefault(ch.get("attribute_name"), set()).add(
            va.text if va is not None else None)
    return out, (str(err) if err else None)


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        tabla = {}
        for nombre, (ini, fin) in GRUPOS.items():
            print("=" * 78)
            print(f"{nombre}")
            for attr, val in ATRIBUTOS:
                out, err = await guardar(ma2, ini, fin, attr, val)
                if out is None:
                    print(f"  {attr:<18} SIN XML  {err}")
                    continue
                ok = attr in out
                vals = sorted(out.get(attr, []))
                dim = sorted(out.get("DIM", []))
                marca = "SI " if ok else "no "
                extra = f"  (DIM queda={dim})" if not ok else ""
                print(f"  {marca} {attr:<18} {vals}{extra}")
                tabla[(nombre, attr)] = ok

        print("=" * 78)
        print("MATRIZ (SI = el fixture acepta el atributo de verdad)")
        print(f"  {'atributo':<20}" + "".join(f"{n.split()[0]:>8}"
                                            for n in GRUPOS))
        for attr, _ in ATRIBUTOS:
            fila = "".join(f"{'  SI' if tabla.get((n, attr)) else '   -':>8}"
                           for n in GRUPOS)
            print(f"  {attr:<20}{fila}")

        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {SEQ}")


if __name__ == "__main__":
    asyncio.run(main())