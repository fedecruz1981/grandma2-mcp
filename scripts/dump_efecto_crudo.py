r"""
Dumpea el XML CRUDO que exporta la consola alrededor de un efecto.

Por que: el parser con ElementTree_find del EffectFlags salia vacio, pero el XML
que yo genero para importar SI lleva EffectFlags/Rate/Low/High/Phase/Width. O
la consola los descarta al importar, o estan en otro nivel del arbol y el
parser los busca en el lugar equivocado. Este script no interpreta nada: solo
muestra el texto, para ver la estructura real.

Uso: python scripts\dump_efecto_crudo.py [secuencia]
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


async def main():
    seq = int(sys.argv[1]) if len(sys.argv) > 1 else 157
    sello = int(time.time()) % 100000
    tag = f"raw_{seq}_{sello}"
    f = EXPORT / f"{tag}.xml"
    f.unlink(missing_ok=True)
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")

    async with Ma2() as ma2:
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
        await ma2.drain()
        await ma2._raw("Clear")

    if not (f.exists() and f.stat().st_size > 0):
        print("no se pudo exportar")
        return 1
    txt = f.read_text(encoding="utf-8", errors="replace")
    f.unlink(missing_ok=True)

    print(f"export de la seq {seq}: {len(txt)} bytes")
    print()
    print("=" * 76)
    print("PRIMERA APARICION DE UN EFECTO, TEXTO CRUDO (900 caracteres)")
    print("=" * 76)
    m = re.search(r'<Effect\b', txt)
    if not m:
        print("no hay ningun <Effect> en el export")
        return 0
    ini = max(0, m.start() - 320)
    print(txt[ini:ini + 900])

    print()
    print("=" * 76)
    print("CUANTAS VECES APARECE CADA COSA EN TODO EL EXPORT")
    print("=" * 76)
    for tag_ in ("<Effect ", "<EffectFlags", "<EffectRate>", "<EffectLow>",
                 "<EffectHigh>", "<EffectPhase>", "<EffectWidth>",
                 'attribute_name="PAN"', 'attribute_name="TILT"'):
        print(f"  {tag_:<32} {txt.count(tag_)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))