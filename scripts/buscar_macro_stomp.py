r"""
Busca los MACROS de stomp en la consola (el operador dice que stomp es un macro,
no una propiedad del XML de secuencia).

Por que: se尝试 escribir `stomp` como atributo del XML (Value / CueData / Cue /
elemento <Stomp/>) y la consola lo descarta en silencio en los cuatro casos. O
sea que el stomp de esta consola se dispara con un macro, y ese macro hay que
encontrarlo por nombre.

Muestra cada comando con su respuesta CRUDA (regla del operador: telnet directo
documentado, sin MCP).

Uso: python scripts\buscar_macro_stomp.py
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
    """Envia un comando y devuelve el texto crudo, sin filtrar nada."""
    await ma2.drain()
    await ma2._raw(cmd)
    buf = await ma2._read_until_prompt(max_wait=espera)
    txt = ANSI.sub("", buf or "")
    if "Overwrite" in txt:
        await ma2.drain()
        await ma2._raw("2")
        await ma2._read_until_prompt(max_wait=3.0)
        return "(respondido 2 = Cancel a un dialogo de Overwrite)"
    return "\n".join(x.rstrip() for x in txt.replace("\r", "\n").split("\n")
                     if x.strip())


async def main():
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")
    async with Ma2() as ma2:
        print()
        print("=" * 78)
        print("1. ENTRAR AL POOL DE MACROS Y LISTAR")
        print("=" * 78)
        for cmd in ("cd /", "cd Macros", "list"):
            print(f"\n  >>> {cmd}")
            print("      " + (await crudo(ma2, cmd)).replace("\n", "\n      ")[:3000])

        print()
        print("=" * 78)
        print("2. OTRAS FORMAS DE PEDIR EL LISTADO DE MACROS")
        print("=" * 78)
        for cmd in ("cd /", "Macro ?", "macro ?", "list macro", "List Macros"):
            print(f"\n  >>> {cmd}")
            print("      " + (await crudo(ma2, cmd)).replace("\n", "\n      ")[:2000])

        await ma2.drain()
        await ma2._raw("Clear")
        await ma2._read_until_prompt(max_wait=3.0)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))