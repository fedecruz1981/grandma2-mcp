"""Verificación en vivo de lo que hasta ahora era inferencia.

Dos preguntas que dejé sin responder porque no había consola:

1. ¿`list cue 3.0 sequence N` falla de verdad, o la consola lo acepta?
   Toda la cadena de correcciones depende de esto.
2. ¿La consola devuelve los cues con el prefijo de objeto que asumo?

Solo lectura. No escribe nada en el show.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

SEQS = (156, 157, 161)


def cuerpo(resp) -> list[str]:
    """Líneas de dato. Ma2Response.body ya saca eco, cabeceras y prompt."""
    return [ln.strip() for ln in resp.body if ln.strip()]


def vacio(resp) -> bool:
    return "NO OBJECTS" in resp.raw.upper()


def errores(resp) -> list[str]:
    return [ln.strip() for ln in resp.errors]


async def main() -> None:
    c = Ma2()
    await c.connect()
    print("conectado\n")

    print("=" * 72)
    print("PREGUNTA 1 — ¿la consola acepta el cue 3.0?")
    print("=" * 72)
    for seq in SEQS:
        for cue in ("3", "3.0", "1", "1.0"):
            resp = await c.cmd(f"list cue {cue} sequence {seq}")
            lineas = cuerpo(resp)
            vacio_ = vacio(resp)
            marca = "VACIO" if vacio_ else f"{len(lineas)} lineas"
            print(f"  list cue {cue:<4} sequence {seq:<4} -> {marca}")
            if errores(resp):
                print(f"        errores: {errores(resp)}")
        print()

    print("=" * 72)
    print("PREGUNTA 2 — ¿las tres secuencias dan contenido distinto?")
    print("=" * 72)
    contenidos = {}
    for seq in SEQS:
        resp = await c.cmd(f"list cue 1 sequence {seq}")
        contenidos[seq] = cuerpo(resp)
        print(f"  sequence {seq}: {len(contenidos[seq])} lineas")
        for ln in contenidos[seq][:3]:
            print(f"      {ln}")
    distintos = contenidos[156] != contenidos[157]
    print(f"\n  >> la 156 y la 157 difieren: {distintos}")
    if not distintos:
        print("     OJO: si son iguales, la forma del comando no distingue la secuencia.")

    print()
    print("=" * 72)
    print("PREGUNTA 3 — ¿qué spellings devuelve el listado de cues?")
    print("=" * 72)
    for seq in SEQS[:1]:
        resp = await c.cmd(f"list cue sequence {seq}")
        print(f"  --- list cue sequence {seq} ---")
        for ln in cuerpo(resp)[:8]:
            print(f"      {ln}")

    print()
    print("=" * 72)
    print("PREGUNTA 4 — ¿qué hace la consola con un cue imposible?")
    print("=" * 72)
    for cue, seq in (("999", 156), ("3.0", 156), ("1.1", 156), ("abc", 156)):
        resp = await c.cmd(f"list cue {cue} sequence {seq}")
        primera = cuerpo(resp)
        print(f"  list cue {cue:<4} sequence {seq}:")
        print(f"      {primera[:2] if primera else '(sin lineas de dato)'}")
        if errores(resp):
            for ln in resp.raw.splitlines():
                if "Error" in ln:
                    print(f"      ERROR: {ln.strip()}")
                    break

    await c.close()


asyncio.run(main())