r"""
Configura la funcion del boton del executor HUMO (3.111).

El boton original no era un Go comun: era un boton de funcion.
Sintaxis (manual MA2): Assign [Funcion] At Executor [id]
  Assign Toggle At Executor 3.111   -> apretar enciende, apretar de nuevo apaga
  Assign Temp   At Executor 3.111   -> encendido mientras se mantiene apretado

Uso: python scripts\apply_humo.py [toggle|temp]
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

FUNC = (sys.argv[1] if len(sys.argv) > 1 else "toggle").lower()


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ma2.cmd("cd /")
        print("  antes:")
        for ln in (await ma2.cmd("List Executor 3.111")).lines:
            if ln.strip():
                print(f"    {ln.strip()}")

        await ma2.cmd("cd /")
        cmd = f"Assign {FUNC} At Executor 3.111"
        r = await ma2.cmd(cmd)
        print(f"\n  {cmd}  ->  "
              f"{'ok' if not r.errors else 'ERR ' + str(r.errors)}")

        await ma2.cmd("cd /")
        print("\n  despues:")
        for ln in (await ma2.cmd("List Executor 3.111")).lines:
            if ln.strip():
                print(f"    {ln.strip()}")

        await ma2.cmd("cd /")
        await ma2.cmd("SaveShow /noconfirm")
        print("\n  show guardado")


if __name__ == "__main__":
    asyncio.run(main())
