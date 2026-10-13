r"""
Verifica con cuidado la funcion de boton de las escenas 3.101-3.106.

assign_executors.py solo hizo `Assign Sequence N Executor P.B`, que en un
scratch virgen da Go (12299). Pero dump_buttons.py mostro 12307 en 3.101.
Hay que confirmar si es Toggle de verdad o un artefacto, y ver como depende
del tipo de secuencia (1 cue vs multi-cue).

Uso: python scripts\check_scene_buttons.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")


async def exportar(ma2, tipo, ref, nombre):
    f = EXPORT_DIR / f"{nombre}.xml"
    if f.exists():
        f.unlink()
    await ma2.cmd("cd /")
    r = await ma2.cmd(f'Export {tipo} {ref} "{nombre}"')
    if r.errors:
        return None
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

        print("  executors de escena:")
        for btn in (101, 102, 103, 104, 105, 106):
            b = await exportar(ma2, "Executor", f"3.{btn}", "sb")
            print(f"    3.{btn}: {b}")

        print("\n  secuencia 156 (multi-cue):")
        b = await exportar(ma2, "Sequence", "156", "sq156")
        print(f"    seq156: {b}")

        print("\n  scratch: default segun tipo de secuencia")
        for ex, seq, etq in (("9.1", "156", "multi-cue"),
                             ("9.2", "20", "1 cue"),
                             ("9.3", "161", "multi-cue")):
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Executor {ex}")
            await ma2.cmd("cd /")
            await ma2.cmd(f"Assign Sequence {seq} Executor {ex}")
            b = await exportar(ma2, "Executor", ex, "sb")
            print(f"    {ex} <- seq {seq} ({etq}): {b}")
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Executor {ex}")

        await ma2.cmd("cd /")
        await ma2.cmd("SaveShow /noconfirm")


if __name__ == "__main__":
    asyncio.run(main())
