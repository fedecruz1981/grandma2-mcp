"""¿Qué comando trae los VALORES de un cue?

`list cue N sequence M` devuelve la fila de la tabla: trigger, modo, loop,
tiempos. No trae valores de canal. Eso rompe la premisa de diff_cues y de
detect_tracking_leaks.

Acá pruebo las formas candidatas sobre un cue que sí tiene valores (INTI Y LUNA,
cuel 1 de la 156 tiene 749 valores grabados).

Solo lectura.
"""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

SEQ = 156


def tiene_valores(lineas) -> bool:
    """Un valor de canal tiene forma Dimmer / Dimmer= / Fixture 1."""
    return any(
        re.search(r"(?i)\b(Dimmer|Color|Gobo|Pan|Tilt|Intensity)\b\s*[= ]\s*\d", ln)
        for ln in lineas
    )


async def main():
    c = Ma2()
    await c.connect()

    print("=" * 74)
    print("0 — ¿la 156 tiene cues con contenido?")
    print("=" * 74)
    r = await c.cmd(f"list cue sequence {SEQ}")
    ids = []
    for ln in r.body:
        m = re.match(r"^\s*Cue\s+(\d+(?:\.\d+)?)\b", ln.strip())
        if m:
            ids.append(m.group(1))
    print(f"  cues: {ids}")

    print()
    print("=" * 74)
    print("1 — Candidatas para leer los valores de un cue")
    print("=" * 74)

    candidatas = [
        f"list cue 1 sequence {SEQ}",
        f"cd Sequence {SEQ} Cue 1",
        "list",
        "cd /",
        f"cd Sequence {SEQ} Cue 1",
        "list cue",
        "cd /",
        f"cd Sequence {SEQ} Cue 1",
        "list preset",
        "cd /",
        f"cd Sequence {SEQ} Cue 1",
        "info",
        "cd /",
        f"cd Sequence {SEQ} Cue 1",
        "info attribute",
        "cd /",
        f"cd Sequence {SEQ} Cue 1",
        "list preset 1",
        "cd /",
        f"cd Sequence {SEQ} Cue 1",
        "pd",
        "cd /",
        "list pd",
    ]

    bloque = []
    for cmd in candidatas:
        rr = await c.cmd(cmd)
        bloque.append((cmd, rr.body))

    print()
    for cmd, cuerpo in bloque:
        vals = tiene_valores(cuerpo)
        print(f"\n  {'>>> ' + cmd}")
        print(f"      {len(cuerpo)} lineas   {'TIENE VALORES' if vals else 'sin valores de canal'}")
        for ln in cuerpo[:6]:
            print(f"        {ln.rstrip()[:120]}")

    await c.close()
    print("\n  (cd en /)")


asyncio.run(main())
