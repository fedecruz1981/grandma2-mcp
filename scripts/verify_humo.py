r"""Verifica que funcion tiene el boton del executor HUMO (3.111).

Se prueba List sobre ExecButton1/2/3, que es donde vive la "button function".

Uso: python scripts\verify_humo.py [toggle|temp]   (aplica y verifica)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402


async def dump(ma2, etiqueta):
    print(f"  {etiqueta}")
    for b in (1, 2, 3):
        await ma2.cmd("cd /")
        r = await ma2.cmd(f"List ExecButton{b} 3.111")
        lineas = [x.strip() for x in r.lines
                  if x.strip() and not x.startswith("Executing")]
        for ln in lineas[:3]:
            print(f"    EB{b}: {ln[:150]}")


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        await dump(ma2, "estado actual:")
        if len(sys.argv) > 1:
            func = sys.argv[1]
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"Assign {func} At Executor 3.111")
            print(f"\n  Assign {func} At Executor 3.111 -> "
                  f"{'ok' if not r.errors else 'ERR ' + str(r.errors)}")
            await dump(ma2, "despues:")
            await ma2.cmd("cd /")
            await ma2.cmd("SaveShow /noconfirm")
            print("  show guardado")


if __name__ == "__main__":
    asyncio.run(main())
