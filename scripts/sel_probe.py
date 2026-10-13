"""
Encuentra (a) como se vuelve al nivel raiz y (b) la sintaxis correcta de
seleccion de fixtures.

Contexto: el write path YA funciona -- `Store Cue 1 Sequence 156 /noconfirm`
creo la secuencia 156 y guardo los valores del programador. Pero los valores
fueron a los fixtures 5-8 (Stromber) porque la seleccion `Fixture 23.1 Thru
30.1` dio ILLEGAL RANGE y quedo la seleccion anterior.

Read-back: se usa el Programmer, que es estado de consola (no del show).
Se prueba cada variante y se lee que fixtures quedaron seleccionados.

Uso: python scripts/sel_probe.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402)


async def selection(ma2):
    """Lee que hay seleccionado. Busca en el prompt o en un list."""
    r = await ma2.cmd("")
    return r.prompt


async def main():
    async with Ma2() as ma2:
        print(f"prompt inicial: {await ma2.at_prompt()!r}\n")

        print("#" * 78)
        print("# VOLVER AL ROOT")
        await ma2.cmd("cd Sequence 137 Cue 1")
        print("  dentro de        :", (await ma2.at_prompt()))
        for c in ["Top", "cd ..", "cd /", "cd ~"]:
            r = await ma2.cmd(c)
            print(f"  {c:<10} -> prompt={r.prompt!r}"
                  f"{'  ERR:' + str(r.errors) if r.errors else ''}")

        print("\n" + "#" * 78)
        print("# SINTAXIS DE SELECCION (verificando con el Programmer)")
        # Volver a raiz para poder entrar a Sequences
        await ma2.cmd("Top")
        print("  root tras Top    :", (await ma2.at_prompt()))

        VARIANTES = [
            "cd LiveSetup/Layers 4",
            "Fixture 23 Thru 30",
            "Fixture 23.1",
            "Fixture 23 Thru 30.1",
            "Fixture 23.1 Thru 30",
            "At 23.1",
        ]
        for c in VARIANTES:
            r = await ma2.cmd(c)
            print(f"\n  >>> {c}")
            print(f"      prompt={r.prompt!r}"
                  f"{'  ERR:' + str(r.errors) if r.errors else '  ok'}")
            # leer el programador
            p = await ma2.cmd("cd Programmer")
            lst = await ma2.cmd("list")
            lineas = [x for x in lst.body if x.strip()][:6]
            print(f"      prompt tras cd Programmer = {p.prompt!r}")
            for ln in lineas:
                print(f"        {ln[:150]}")


if __name__ == "__main__":
    asyncio.run(main())
