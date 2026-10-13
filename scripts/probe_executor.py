r"""
Prueba como se configura la funcion del boton de un executor por telnet.

El boton HUMO original era toggle (apretar/soltar). Un `Assign Sequence` da un
Go normal. Hay que cambiar la "button function" del executor.

Se prueban:
  - List Executor 3.111        -> que informa
  - Assign Executor 3.111 /toggle
  - Assign Executor 3.111 /temp
y se relee para ver si el comando existe (error o no).

Uso: python scripts\probe_executor.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

CMDS = [
    "List Executor 3.111",
    "List Executor 3.110",
    "Assign Executor 3.111 /toggle",
    "List Executor 3.111",
    "Assign Executor 3.111 /temp",
    "Assign Executor 3.111",
    "List Executor 3.111",
]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for c in CMDS:
            await ma2.cmd("cd /")
            r = await ma2.cmd(c)
            print(f">>> {c}")
            print(f"    err={r.errors}")
            for ln in [x for x in r.body if x.strip()][:14]:
                print(f"    {ln.strip()[:130]}")


if __name__ == "__main__":
    asyncio.run(main())
