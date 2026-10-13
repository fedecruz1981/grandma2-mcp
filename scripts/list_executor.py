r"""Muestra las lineas completas de List Executor para ver los campos.

Uso: python scripts\list_executor.py [n]
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402


async def main():
    objetivo = sys.argv[1] if len(sys.argv) > 1 else None
    async with Ma2() as ma2:
        await ma2.at_prompt()
        cmds = ([f"List Executor {objetivo}"] if objetivo
                else ["List Executor 3.111", "List Executor 3.110",
                      "List Executor 3.101"])
        for c in cmds:
            await ma2.cmd("cd /")
            r = await ma2.cmd(c)
            print(f">>> {c}")
            for ln in r.lines:
                if ln.strip():
                    print(f"    {ln.strip()}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
