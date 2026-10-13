r"""
Asigna la secuencia HUMO (20) a un boton libre de la Page 3.

Uso: python scripts\put_humo.py [boton]      (default 111)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

PAGE = 3
SEQ = 20
BTN = int(sys.argv[1]) if len(sys.argv) > 1 else 111


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ma2.cmd("cd /")
        p = await ma2.cmd(f"cd Executor {PAGE}.{BTN}")
        print(f"  3.{BTN} antes:   {p.prompt!r}")
        await ma2.cmd("cd /")
        r = await ma2.cmd(f"Assign Sequence {SEQ} Executor {PAGE}.{BTN}")
        print(f"  asignar seq {SEQ} (HUMO) -> 3.{BTN}: "
              f"{'ok' if not r.errors else 'ERR ' + str(r.errors)}")
        await ma2.cmd("cd /")
        p = await ma2.cmd(f"cd Executor {PAGE}.{BTN}")
        print(f"  3.{BTN} despues: {p.prompt!r}")
        await ma2.cmd("cd /")
        await ma2.cmd("SaveShow /noconfirm")
        print("  show guardado")


if __name__ == "__main__":
    asyncio.run(main())
