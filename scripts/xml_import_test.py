r"""
Prueba si `Import` guarda los effects que el comando `At Effect` rechaza.

Casos (una secuencia de 4 cues):
  cue 1: fx1-4  COLOR1=24 + effect 7  -> arcoiris sobre la RUEDA (no hay RGB)
  cue 2: fx1-4  PAN/TILT=50 + effect 13 -> movimiento en los cabezales
  cue 3: fx23-30 DIM=80 + effect 3     -> dimmer PWM en los Protones
  cue 4: fx5-8  COLORRGB1=100 + effect 7 -> control: arcoiris normal

Se importa en la 191, se reexporta y se informa que quedo guardado.
Uso: python scripts\xml_import_test.py
"""
import asyncio
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqxml  # noqa: E402
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
SEQ = 191


def resumen(ruta):
    root = ET.parse(ruta).getroot()
    out = {}
    for cue in root.iter(f"{NS}Cue"):
        ci = cue.get("index")
        if ci is None:
            continue
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            ef = cd.find(f"{NS}Effect")
            if ch is None:
                continue
            out.setdefault(int(ci), []).append((
                int(ch.get("fixture_id")), ch.get("attribute_name"),
                va.text if va is not None else None,
                ef.get("name") if ef is not None else None))
    return out


async def main():
    E = []
    c1 = [(fx, "COLOR1", 24, 7, fx - 1, 4) for fx in range(1, 5)]
    c2 = []
    for fx in range(1, 5):
        c2.append((fx, "PAN", 50, 13, fx - 1, 4))
        c2.append((fx, "TILT", 50, 13, fx - 1, 4))
    c3 = [(fx, "DIM", 80, 3, fx - 23, 8) for fx in range(23, 31)]
    c4 = [(fx, "COLORRGB1", 100, 7, fx - 5, 4) for fx in range(5, 9)]

    xml = seqxml.secuencia(SEQ, "XML TEST", [(1, c1), (2, c2), (3, c3), (4, c4)])
    archivo = EXPORT_DIR / "xmltest.xml"
    archivo.write_text(xml, encoding="utf-8")
    print(f"escrito {archivo}  ({len(xml)} bytes)")

    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ma2.cmd("cd /")
        r = await ma2.cmd(f'Import "xmltest" At Sequence {SEQ}')
        for ln in [x for x in r.body if x.strip()][:4]:
            print(f"    {ln.strip()[:140]}")
        await ma2.cmd("cd /")
        await ma2.cmd(f'Export Sequence {SEQ} "xmlchk"')

    d = resumen(EXPORT_DIR / "xmlchk.xml")
    etiquetas = {1: "COLOR1 + effect 7 (arcoiris en la rueda)",
                 2: "PAN/TILT + effect 13 (movimiento cabezales)",
                 3: "DIM + effect 3 (dimmer en Protones fx23-30)",
                 4: "COLORRGB1 + effect 7 (control)"}
    for ci in sorted(d):
        print(f"\n  cue {ci}: {etiquetas.get(ci, '?')}")
        for fx, attr, val, efe in d[ci][:10]:
            marca = "EFFECT" if efe else "      "
            print(f"    {marca} fx{fx:<3} {attr:<12} val={val}  "
                  f"effect={efe}")
        if len(d[ci]) > 10:
            print(f"    ... ({len(d[ci])} filas)")

    async with Ma2() as ma2:
        await ma2.cmd("cd /")
        r = await ma2.cmd(f"Delete Sequence {SEQ}")
        print(f"\n  (secuencia {SEQ} borrada: "
              f"{'ok' if not r.errors else 'ERR'})")


if __name__ == "__main__":
    asyncio.run(main())
