"""Qué devuelve realmente `list cue N sequence M`.

El refactor asume que el cuerpo de la respuesta contiene los DATOS del cue.
La primera sonda en vivo showed que las tres secuencias devuelven texto
idéntico para el cue 1 — y solo tres campos de reproducción, sin valores de
canal. Antes de dar por buena esa premisa, hay que ver un cue que sí tenga
contenido.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402


async def main() -> None:
    c = Ma2()
    await c.connect()

    print("=" * 72)
    print("1 — ¿QUÉ SHOW ESTÁ ABIERTO?")
    print("=" * 72)
    r = await c.cmd("ListVar")
    for linea in r.body:
        s = linea.strip()
        if any(k in s.upper() for k in ("$SHOWFILE", "$VERSION", "$USER", "$FADERPAGE")):
            print(f"  {s}")

    print()
    print("=" * 72)
    print("2 — ¿CUÁNTOS CUES POR SECUENCIA? (156 a 161)")
    print("=" * 72)
    for seq in (156, 157, 158, 159, 160, 161):
        r = await c.cmd(f"list cue sequence {seq}")
        filas = [ln for ln in r.body if ln.strip().startswith("Cue ")]
        print(f"  sequence {seq}: {len(filas)} cues")

    print()
    print("=" * 72)
    print("3 — ¿QUÉ DEVUELVE UN CUE CON CONTENIDO? (sequence 161, todos los cues)")
    print("=" * 72)
    r = await c.cmd("list cue sequence 161")
    ids = []
    for ln in r.body:
        s = ln.strip()
        if s.startswith("Cue "):
            partes = s.split()
            if len(partes) > 1:
                try:
                    ids.append(float(partes[1]))
                except ValueError:
                    pass
    print(f"  cues en la 161: {[int(i) if i.is_integer() else i for i in ids]}")
    for cue in ids:
        rr = await c.cmd(f"list cue {int(cue) if cue.is_integer() else cue} sequence 161")
        print(f"\n  --- cue {cue} ({len(rr.body)} lineas) ---")
        for ln in rr.body:
            print(f"      {ln.rstrip()}")

    print()
    print("=" * 72)
    print("4 — ALTERNATIVA: cd al cue y list. ¿Devuelve los valores?")
    print("=" * 72)
    if ids:
        objetivo = int(ids[0]) if ids[0].is_integer() else ids[0]
        for cmd in (
            f"cd Sequence 161 Cue {objetivo}",
            "list",
            "cd /",
        ):
            rr = await c.cmd(cmd)
            print(f"\n  >>> {cmd}  ({len(rr.body)} lineas)")
            for ln in rr.body[:14]:
                print(f"      {ln.rstrip()}")

    print()
    print("=" * 72)
    print("5 — ¿Y CON pd/attribute sobre el cue?")
    print("=" * 72)
    for cmd in ("list attribute", "cd Sequence 161", "list"):
        rr = await c.cmd(cmd)
        print(f"\n  >>> {cmd}  ({len(rr.body)} lineas)")
        for ln in rr.body[:10]:
            print(f"      {ln.rstrip()}")

    await c.close()
    print("\n  (el cd quedó en Sequence 161; bajá a / en la consola si hace falta)")


asyncio.run(main())