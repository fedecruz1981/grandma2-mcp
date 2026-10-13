r"""
Lee el CONTENIDO de los macros de stomp de la consola.

Por que: `list macro` mostro que existen (1..7), y el 6 es "Stomp running
Effects", que es el que el operador dice que hay que correr antes de grabar los
colores. Pero hay que saber QUE hace antes de meterlo en el flujo: si el stomp
no viaja en el XML de la secuencia (verificado: la consola descarta el atributo
`stomp` en Value, CueData, Cue y como elemento <Stomp/>), entonces el macro es
la parte del mecanismo que todavia no.tenemos.

Ademas lista TODOS los macros (pool Global 1 tiene 7, `List Macros` dijo 13 en
total) por si hay otro de stomp en otro pool.

Uso: python scripts\ver_macro_stomp.py
"""
import asyncio
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


async def crudo(ma2, cmd, espera=6.0):
    await ma2.drain()
    await ma2._raw(cmd)
    buf = await ma2._read_until_prompt(max_wait=espera)
    txt = ANSI.sub("", buf or "")
    if "Overwrite" in txt:
        await ma2.drain()
        await ma2._raw("2")
        await ma2._read_until_prompt(max_wait=3.0)
        return "(Overwrite -> 2)"
    return "\n".join(x.rstrip() for x in txt.replace("\r", "\n").split("\n")
                     if x.strip())


async def main():
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")
    async with Ma2() as ma2:
        print()
        print("=" * 78)
        print("1. TODOS LOS MACROS DE LA CONSOLA (13 segun `List Macros`)")
        print("=" * 78)
        print("  >>> list macro")
        print("      " + (await crudo(ma2, "list macro")).replace("\n", "\n      "))

        print()
        print("=" * 78)
        print("2. CONTENIDO DEL MACRO 6 'Stomp running Effects'")
        print("=" * 78)
        for cmd in ("cd /", "cd Macro 6", "list"):
            print(f"\n  >>> {cmd}")
            print("      " + (await crudo(ma2, cmd)).replace("\n", "\n      ")[:2500])

        print()
        print("=" * 78)
        print("3. LOS OTROS DE STOMP, PARA COMPARAR (2 Stomp Color, 5 Dimmer)")
        print("=" * 78)
        for n in (2, 5):
            print(f"\n  >>> cd Macro {n} / list")
            await crudo(ma2, "cd /")
            await crudo(ma2, f"cd Macro {n}")
            print("      " + (await crudo(ma2, "list")).replace("\n", "\n      ")[:1800])

        await ma2.drain()
        await ma2._raw("Clear")
        await ma2._read_until_prompt(max_wait=3.0)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))