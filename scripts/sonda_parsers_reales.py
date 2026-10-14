r"""Los parsers del repo contra listings REALES de la consola.

Los tests de este repo se escribieron con respuestas inventadas. Con la consola
disponible, capturo las de verdad y veo si los parsers las entienden.

Resultado: la consola antepone el tipo a cada fila ("Sequ", "Macro", "Cue",
"Fixture"), así que el patrón `^\s*(\d+)\s` no matchea ninguna. Ver
doc/CUE-READS-ES.md §11.

Solo lectura: solo envía `list`.
"""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.cue_reads import strip_chrome  # noqa: E402

# El parser que usa find_unused_objects para el listado de secuencias.
RE_SEQ = re.compile(r"^\s*(\d+)\s")
# El parser de macros, en la misma forma.
RE_MACRO = re.compile(r"^\s*(\d+)\s")
# El que usa trace_attribute_lineage para listar secuencias.
RE_LINEAGE = re.compile(r"^\s*(\d+)\s*(.*)$")
# El de find_preset_usages.
RE_CUE_COL = re.match


async def main():
    c = Ma2()
    await c.connect()

    print("=" * 74)
    print("A â€” FORMATO REAL de 'list sequence'")
    print("=" * 74)
    r = await c.cmd("list sequence")
    for ln in r.body[:4]:
        print(f"  |{ln.rstrip()[:100]}")
    filas = [ln for ln in r.body if ln.strip()]
    con_prefijo = sum(1 for ln in filas if re.match(r"^\s*Sequ\s", ln))
    print(f"\n  filas con prefijo 'Sequ': {con_prefijo} de {len(filas)}")
    print(f"  RE_SEQ (^\\s*(\\d+)\\s) matchea: {sum(1 for ln in filas if RE_SEQ.match(ln))}")
    print(f"  RE_LINEAGE matchea:            {sum(1 for ln in filas if RE_LINEAGE.match(ln))}")

    print()
    print("=" * 74)
    print("B â€” FORMATO REAL de 'list macro'")
    print("=" * 74)
    r = await c.cmd("list macro")
    for ln in r.body[:5]:
        print(f"  |{ln.rstrip()[:100]}")
    filas = [ln for ln in r.body if ln.strip()]
    con_prefijo = sum(1 for ln in filas if re.match(r"^\s*Macro\s", ln))
    print(f"\n  filas con prefijo 'Macro': {con_prefijo} de {len(filas)}")
    print(f"  RE_MACRO (^\\s*(\\d+)\\s) matchea: {sum(1 for ln in filas if RE_MACRO.match(ln))}")

    print()
    print("=" * 74)
    print("C â€” FORMATO REAL de 'list preset 1' (pool)")
    print("=" * 74)
    r = await c.cmd("list preset 1")
    for ln in r.body[:6]:
        print(f"  |{ln.rstrip()[:100]}")
    filas = [ln for ln in r.body if ln.strip()]
    con_prefijo = sum(1 for ln in filas if re.match(r"^\s*Preset\s", ln))
    print(f"\n  filas con prefijo 'Preset': {con_prefijo} de {len(filas)}")

    print()
    print("=" * 74)
    print("D â€” strip_chrome sobre una respuesta REAL con datos")
    print("=" * 74)
    r = await c.cmd("list cue 1 sequence 156")
    print("  crudo:")
    for ln in r.raw.splitlines():
        print(f"    |{ln.rstrip()[:110]}")
    print("\n  tras strip_chrome:")
    for ln in strip_chrome(r.raw):
        print(f"    |{ln[:110]}")

    await c.close()


asyncio.run(main())
