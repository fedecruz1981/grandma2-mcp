r"""
Lee los PARAMETROS del ef17 (P/T Cross) que quedaron guardados en los cabezales.

Por que: un efecto puede estar escrito en la secuencia y aun asi no mover nada.
Los parametros que importan son EffectLow/EffectHigh (amplitud del barrido) y
EffectPhase (el desfase entre fixtures). Si los cuatro cabezales tienen Phase 0,
se mueven todos al mismo tiempo: eso no se ve como un barrido, se ve como una
inclinacion sincronizada.

Ademas sirve para mostrar por que el cue de la coreografia de Bigotin (Q11) no
tiene ningun efecto escrito.

Uso: python scripts\ver_efecto_barrido.py
"""
import asyncio
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402
from ma2_telnet import ANSI  # noqa: E402

EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"


async def exportar(ma2, seq, sello):
    tag = f"efs_{seq}_{sello}"
    f = EXPORT / f"{tag}.xml"
    f.unlink(missing_ok=True)
    await ma2.drain()
    await ma2._raw(f"Export Sequence {seq} '{tag}'")
    crudo = await ma2._read_until_prompt(max_wait=6.0)
    if "Overwrite" in ANSI.sub("", crudo or ""):
        await ma2.drain()
        await ma2._raw("2")
        await ma2._read_until_prompt(max_wait=3.0)
    for _ in range(30):
        if f.exists() and f.stat().st_size > 0:
            break
        await asyncio.sleep(0.3)
    if not (f.exists() and f.stat().st_size > 0):
        return None
    root = ET.parse(f).getroot()
    f.unlink(missing_ok=True)
    return root


async def main():
    sello = int(time.time()) % 100000
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")

    async with Ma2() as ma2:
        root = await exportar(ma2, 157, sello)
        await ma2.drain()
        await ma2._raw("Clear")
    if root is None:
        print("no se pudo exportar la 157")
        return 1

    print()
    print("=" * 76)
    print("SEQ 157 - efectos sobre PAN/TILT de los cabezales fx1-4")
    print("=" * 76)
    for cue in root.iter(f"{NS}Cue"):
        idx = cue.get("index")
        if idx is None:
            continue
        filas = []
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            ef = cd.find(f"{NS}Effect")
            if ch is None or ef is None:
                continue
            fx = int(ch.get("fixture_id"))
            if not 1 <= fx <= 4:
                continue
            attr = ch.get("attribute_name")
            if attr not in ("PAN", "TILT"):
                continue
            g = lambda t: (cd.findtext(f"{NS}{t}") or "").strip()  # noqa: E731
            # OJO: los parametros NO son hijos de <Effect>, son hermanos suyos,
            # hijos directos del <CueData>. Buscarlos adentro de <Effect> los
            # hacia parecer vacios cuando en realidad estan todos.
            flags = cd.find(f"{NS}EffectFlags")
            filas.append((fx, attr, ef.get("name"),
                          g("EffectRate"), g("EffectLow"), g("EffectHigh"),
                          g("EffectPhase"), g("EffectWidth"),
                          flags.get("form_index") if flags is not None else "-",
                          flags.get("sub_form_index") if flags is not None else "-"))
        if not filas:
            print(f"  cue {idx:>2}:  (ningun efecto sobre PAN/TILT de los cabezales)")
            continue
        print(f"  cue {idx:>2}:")
        print(f"      fx attr  efecto             rate  low  high  phase width  form/sub")
        for fx, attr, nom, rate, low, high, fase, width, fi, sf in filas:
            print(f"      {fx:>2} {attr:<5} {nom:<16} {rate:>5} {low:>4} {high:>5} "
                  f"{fase:>5} {width:>5}  {fi}/{sf}")

    print()
    print("Que mirar: 'phase' distinto en cada fx = los haces se cruzan (barrido).")
    print("            phase igual en todos    = se mueven juntos (inclinacion).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))