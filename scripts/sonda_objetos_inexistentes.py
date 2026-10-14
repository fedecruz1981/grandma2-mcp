"""¿Qué devuelve la consola cuando se le pide algo que no existe?

Se vio que `list cue abc sequence 156` devolvía la fila del cue 1 en vez de un
error. Si un número inexistente hace lo mismo, entonces toda validación que se
apoye en "NO OBJECTS FOUND" para decidir que un objeto existe está autorizando
basura: un id mal escrito pasa por válido.

Además prueba, contra la consola real, el aviso de eco mal cotejado que se
agregó en 6d0c6e5 y que nunca se verificó en vivo.

Solo lectura.
"""

import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from ma2_telnet import Ma2  # noqa: E402
from src.cue_reads import classify  # noqa: E402
from src.telnet_client import echo_matches_command  # noqa: E402

SEQ_REAL = 156


async def main():
    c = Ma2()
    await c.connect()
    print("show abierto: ", (await c.cmd("ListVar")).body and "", end="")
    for ln in (await c.cmd("ListVar")).body:
        if "$SHOWFILE" in ln.upper():
            print(f"  {ln.strip()}")
    print()

    print("=" * 76)
    print("1 — LA FILA DE REFERENCIA (lo que el cue 1 devuelve de verdad)")
    print("=" * 76)
    ref = await c.cmd(f"list cue 1 sequence {SEQ_REAL}")
    for ln in ref.body:
        print(f"  |{ln.rstrip()[:110]}")

    print()
    print("=" * 76)
    print("2 — PEDIR COSAS QUE NO EXISTEN")
    print("=" * 76)
    casos = [
        (f"list cue 1 sequence {SEQ_REAL}",   "referencia: el cue 1, que sí existe"),
        (f"list cue 99 sequence {SEQ_REAL}",  "cue 99: no existe"),
        (f"list cue 0 sequence {SEQ_REAL}",   "cue 0: no existe"),
        (f"list cue abc sequence {SEQ_REAL}", "id no numérico"),
        (f"list cue 1 sequence 999",          "sequence 999: no existe"),
        (f"list cue 1 sequence abc",          "sequence no numérica"),
        (f"list cue -1 sequence {SEQ_REAL}",  "cue negativo"),
        (f"list cue 1.99 sequence {SEQ_REAL}", "sub-cue inexistente"),
    ]
    for cmd, desc in casos:
        r = await c.cmd(cmd)
        filas = [ln for ln in r.body if ln.strip().startswith("Cue ")]
        igual = r.raw == ref.raw
        print(f"\n  {cmd}")
        print(f"    {desc}")
        print(f"    -> {'VACIO' if not filas else str(len(filas)) + ' fila(s)'}"
              f"{'   IDENTICO AL CUE 1' if igual else ''}")
        if filas:
            print(f"       {filas[0].strip()[:100]}")
        if r.errors:
            print(f"       errores: {r.errors}")

    print()
    print("=" * 76)
    print("3 — ¿classify() marca correctamente lo que la consola devuelve?")
    print("=" * 76)
    for cmd, desc in casos[:6]:
        r = await c.cmd(cmd)
        read = classify(r.raw, cmd)
        marca = "found" if read.found else "NOT FOUND"
        print(f"  {cmd:<34} {marca:<10} rejected={read.rejected}"
              f"   ({desc})")

    print()
    print("=" * 76)
    print("4 — EL AVISO DE ECO, en vivo (agregado en 6d0c6e5)")
    print("=" * 76)
    for cmd, desc in (
        (f"list cue 1 sequence {SEQ_REAL}", "comando bien formado"),
        ("list cue 1 sequence /",           "con separador de más"),
        ("NotAKeyword 1",                    "keyword inexistente"),
        ("cd / 1",                           "argumento raro"),
    ):
        r = await c.cmd(cmd)
        match = echo_matches_command(r.raw, cmd)
        echo_line = next(
            (ln.strip() for ln in r.raw.splitlines() if "Executing" in ln), ""
        )
        print(f"\n  enviado : {cmd}")
        print(f"  eco     : {echo_line[:100]}")
        print(f"  matchea : {match}   ({desc})")

    await c.close()


asyncio.run(main())