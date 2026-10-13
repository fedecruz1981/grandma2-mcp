r"""
Verifica que el arco de color de los CABEZALES quedara escrito en la consola.

Lo que se busca, cue por cue, en el COLOR1 de fx1..fx4 (la rueda):
  Q1  -> 5.5 / 8 / 13 / 24   (Rojo / Amarillo / Verde / Azul) = arcoiris entero
  Q2  -> 5.5 / 8 / 0 / 0     (2 de 4 con color)
  Q19 -> 8 / 0 / 0 / 0        (1 de 4)
  Q24 -> 24 / 8 / 0 / 0       (2 de 4)
  Q25 -> 8 / 0 / 0 / 0        (1 de 4)
  Q35 -> 0 / 0 / 0 / 0        (0 de 4)
  Q46 -> 29 / 0 / 0 / 0       (1 de 4, el amague)
  Q49 -> 29 / 8 / 0 / 0       (2 de 4)
  Q50 -> 5.5 / 8 / 13 / 24    (arcoiris entero otra vez = el de Q1)

Y ademas:
  Q4  y Q13 -> los 6 grupos en Azul hielo (32.5), el congelado va TODO azul
  Q3  -> los cabezales con ef6 (el parpadeo del guion)

Exporta las secuencias a XML con nombre unico (si el archivo ya existe la
consola abre un dialogo de Overwrite y se traba) y no modifica nada.

Uso: python scripts\ver_arco_cabezales.py
"""
import asyncio
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402
from ma2_telnet import ANSI  # noqa: E402

EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")

# Q1 y Q50 son el cue 1 de la seq 156 y el cue 20 de la seq 161
ESPERADO = {
    156: {1: (5.5, 8.0, 13.0, 24.0), 2: (5.5, 8.0, 0.0, 0.0)},
    161: {1: (5.5, 8.0, 13.0, 24.0)},      # Q50 clico
    160: {}, 161: {},
}
# Q19->cue 4 de 159, Q24->cue 1 de 160, Q25->cue 2 de 160,
# Q35->cue 4 de 161, Q46->cue 15 de 161, Q49->cue 18 de 161
MAS = {
    (159, 4): (8.0, 0.0, 0.0, 0.0),
    (160, 1): (24.0, 8.0, 0.0, 0.0),
    (160, 2): (8.0, 0.0, 0.0, 0.0),
    (161, 4): (0.0, 0.0, 0.0, 0.0),
    (161, 15): (29.0, 0.0, 0.0, 0.0),
    (161, 18): (29.0, 8.0, 0.0, 0.0),
}
RUEDA_NOMBRE = {0.0: "Blanco", 5.5: "Rojo", 8.0: "Amarillo", 13.0: "Verde",
                24.0: "Azul", 29.0: "Rosa", 32.5: "Cian", 15.5: "Morado",
                20.0: "Ambar", 40.5: "Cian claro"}


def color1_por_cue(txt):
    """-> {indice_cue: [COLOR1 de fx1..fx4]} leyendo el XML de la consola.

    Se usa ElementTree y no regex: el export de la consola viene con namespace
    XML ({http://schemas.malighting.de/grandma2/xml/MA}) y los Channel van
    dentro de CueData, igual que en build_sequences.resumen_xml.
    """
    import xml.etree.ElementTree as ET
    NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
    cues = {}
    root = ET.fromstring(txt)
    for cue in root.iter(f"{NS}Cue"):
        idx = cue.get("index")
        if idx is None:
            continue
        col = {}
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            if ch is None or ch.get("attribute_name") != "COLOR1":
                continue
            fx = int(ch.get("fixture_id"))
            if 1 <= fx <= 4:
                try:
                    col[fx] = round(float(va.text), 1)
                except (TypeError, ValueError, AttributeError):
                    col[fx] = va.text if va is not None else None
        cues[int(idx)] = [col.get(i) for i in (1, 2, 3, 4)]
    return cues


def _fmt(vals):
    if vals is None:
        return "(sin COLOR1)"
    return " / ".join(
        (f"{v:g}" if isinstance(v, float) else str(v)) for v in vals)


def _nombres(vals):
    if vals is None:
        return "?"
    out = []
    for v in vals:
        if isinstance(v, float):
            out.append(RUEDA_NOMBRE.get(v, f"{v:g}"))
        else:
            out.append(str(v))
    return "  ".join(out)


async def main():
    sello = int(time.time()) % 100000
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")
    fallos = 0

    async with Ma2() as ma2:
        for seq in (156, 159, 160, 161):
            tag = f"arc_{seq}_{sello}"
            f = EXPORT / f"{tag}.xml"
            f.unlink(missing_ok=True)
            await ma2.drain()
            await ma2._raw(f"Export Sequence {seq} '{tag}'")
            crudo = await ma2._read_until_prompt(max_wait=6.0)
            txt = ANSI.sub("", crudo or "")
            if "Overwrite" in txt:
                await ma2.drain()
                await ma2._raw("2")
                await ma2._read_until_prompt(max_wait=3.0)
            for _ in range(30):
                if f.exists() and f.stat().st_size > 0:
                    break
                await asyncio.sleep(0.3)
            if not (f.exists() and f.stat().st_size > 0):
                print(f"\n  seq {seq}: no se pudo exportar")
                fallos += 1
                continue
            xml = f.read_text(encoding="utf-8", errors="replace")
            f.unlink(missing_ok=True)
            cues = color1_por_cue(xml)
            print(f"\n" + "=" * 76)
            print(f"SEQ {seq}  --  COLOR1 de los 4 cabezales, cue por cue")
            print("=" * 76)
            for idx in sorted(cues):
                vals = cues[idx]
                print(f"  cue {idx:>2}: {_fmt(vals):<28}  {_nombres(vals)}")

        await ma2.drain()
        await ma2._raw("Clear")

    print()
    print("=" * 76)
    print("COMPROBACION DE LOS PUNTOS CLAVE")
    print("=" * 76)
    return fallos


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))