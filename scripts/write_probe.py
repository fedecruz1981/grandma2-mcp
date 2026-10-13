"""
Sondeo de solo lectura: comandos de escritura de secuencias y cues.

Objetivo: descubrir la sintaxis exacta para
  - crear una secuencia nueva
  - entrar a un cue
  - setear atributos de un fixture dentro del cue

`help` en MA2 devuelve "Syntax:<keyword>" sin operandos, asi que la info
real hay que sacarla de la palabra clave y de la estructura del prompt.

No escribe nada.
Uso: python scripts/write_probe.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402)

HELPS = [
    "help Create", "help Sequence", "help Cue", "help Store",
    "help Set", "help Assign", "help Attribute", "help At",
    "help Go", "help Clear", "help Park", "help Label",
    "help SetAttribute", "help Change", "help Timecode",
]

NAVEGACION = [
    "cd Sequences 156",     # existe?
    "cd Sequences 155",
    "cd Sequences 1",
    "cd Sequences 1 Cue 1",
    "cd Sequences 900",     # no deberia existir
]


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()}\n")
        print("#" * 78)
        print("# HELP (sintaxis declarada)")
        for c in HELPS:
            r = await ma2.cmd(c)
            txt = [x for x in r.body if x.strip()]
            print(f"  {c:<22} -> {txt[0].strip() if txt else '(vacio)'}"
                  f"{'  ERR:' + str(r.errors) if r.errors else ''}")

        print("\n" + "#" * 78)
        print("# NAVEGACION (solo cd, no modifica)")
        for c in NAVEGACION:
            r = await ma2.cmd(c)
            print(f"  {c:<26} -> prompt={r.prompt!r}"
                  f"{'  ERR:' + str(r.errors) if r.errors else ''}")

        # el prompt de una secuencia dice como se llama el cue actual
        print("\n" + "#" * 78)
        print("# ESTRUCTURA del prompt dentro de un cue")
        await ma2.cmd("cd Sequences 137")
        print("  seq 137      :", (await ma2.at_prompt()))
        r = await ma2.cmd("cd Sequences 137 Cue 1")
        print("  seq137 cue1  :", r.prompt)
        r = await ma2.cmd("cd Sequences 137 Cue 1 Fixture 23")
        print("  +fixture 23  :", r.prompt)
        r = await ma2.cmd("list")
        for ln in [x for x in r.body if x.strip()][:8]:
            print("     ", ln[:160])


if __name__ == "__main__":
    asyncio.run(main())
