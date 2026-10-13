r"""
Busca el objeto HUMO que estaba en el boton 3.106 antes de reasignarlo.

Al hacer `Assign Sequence 161 Executor 3.106` se reemplazo el executor, pero la
secuencia (u objeto) HUMO no se borra: solo queda sin executor. Hay que
encontrarla para reasignarla al 3.107.

Se prueban varias formas de nombrarla (Sequence/Executor/Assignment) y se lee
el prompt, que es el unico read-back fiable.

Uso: python scripts\find_humo.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

CANDIDATOS = [
    'cd Sequence "HUMO"',
    'cd Sequence "humo"',
    'cd Sequence "Humo"',
    'cd Macro "HUMO"',
    'cd Sequences /',
    'cd /',
    'List Sequence',
]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for c in CANDIDATOS:
            await ma2.cmd("cd /")
            r = await ma2.cmd(c)
            print(f">>> {c}")
            print(f"    prompt={r.prompt!r} err={r.errors}")
            for ln in [x for x in r.body if x.strip()][:8]:
                print(f"    {ln.strip()[:120]}")


if __name__ == "__main__":
    asyncio.run(main())
