r"""
Mide la funcion de boton por defecto en un executor virgen.

En la Page 3 todos los botones muestran <Button>12307</Button>, que segun el
mapeo seria Toggle. Para saber si el default al asignar una secuencia es Go o
Toggle, se usa un executor scratch (Page 9) y se exporta tras cada paso.

Al final borra el scratch y deja HUMO (3.111) en Toggle.

Uso: python scripts\fresh_default_test.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
SCRATCH = "9.1"


async def botones(ma2, ex):
    f = EXPORT_DIR / "fresh.xml"
    if f.exists():
        f.unlink()
    await ma2.cmd("cd /")
    await ma2.cmd(f'Export Executor {ex} "fresh"')
    for _ in range(12):
        if f.exists() and f.stat().st_size > 0:
            break
        await asyncio.sleep(0.3)
    if not f.exists():
        return None
    txt = f.read_text(encoding="utf-8", errors="replace")
    return re.findall(r"<Button>(\d+)</Button>", txt)


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()

        # limpiar por si quedo algo
        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Executor {SCRATCH}")
        await asyncio.sleep(0.3)

        await ma2.cmd("cd /")
        r = await ma2.cmd(f"Assign Sequence 20 Executor {SCRATCH}")
        print(f"  Assign Sequence 20 Executor {SCRATCH}: "
              f"{'ok' if not r.errors else r.errors}")
        print(f"    default        -> {await botones(ma2, SCRATCH)}")

        for etq, cmd in [("Toggle", f"Assign Toggle At Executor {SCRATCH}"),
                         ("Go", f"Assign Go At Executor {SCRATCH}"),
                         ("Temp", f"Assign Temp At Executor {SCRATCH}")]:
            await ma2.cmd("cd /")
            await ma2.cmd(cmd)
            print(f"    {etq:<14} -> {await botones(ma2, SCRATCH)}")

        # borrar scratch
        await ma2.cmd("cd /")
        r = await ma2.cmd(f"Delete Executor {SCRATCH}")
        print(f"  Delete Executor {SCRATCH}: "
              f"{'ok' if not r.errors else r.errors}")

        # dejar HUMO en Toggle
        await ma2.cmd("cd /")
        r = await ma2.cmd("Assign Toggle At Executor 3.111")
        print(f"  HUMO 3.111 -> Toggle: "
              f"{'ok' if not r.errors else r.errors}"
              f"   botones={await botones(ma2, '3.111')}")
        await ma2.cmd("cd /")
        await ma2.cmd("SaveShow /noconfirm")
        print("  show guardado")


if __name__ == "__main__":
    asyncio.run(main())
