r"""
Mapea que codigo <Button> corresponde a cada funcion de boton en MA2.

El default (Go) parece ser 12307. Se prueban varias funciones sobre el executor
HUMO (3.111) y se exporta el executor para leer el codigo resultante.

Uso: python scripts\map_button_funcs.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")

ENSAYOS = [
    ("(default, sin tocar)", None),
    ("Go @ Executor", "Assign Go At Executor 3.111"),
    ("Toggle @ Executor", "Assign Toggle At Executor 3.111"),
    ("Toggle @ ExecButton1", "Assign Toggle At ExecButton1 3.111"),
    ("Temp @ Executor", "Assign Temp At Executor 3.111"),
    ("Temp @ ExecButton1", "Assign Temp At ExecButton1 3.111"),
    ("Flash @ ExecButton1", "Assign Flash At ExecButton1 3.111"),
    ("Flash @ Executor", "Assign Flash At Executor 3.111"),
    ("Swop @ Executor", "Assign Swop At Executor 3.111"),
    ("On @ Executor", "Assign On At Executor 3.111"),
    ("Off @ Executor", "Assign Off At Executor 3.111"),
]


async def exportar(ma2):
    f = EXPORT_DIR / "btnmap.xml"
    if f.exists():
        f.unlink()
    await ma2.cmd("cd /")
    r = await ma2.cmd('Export Executor 3.111 "btnmap"')
    if r.errors:
        return None, r.errors
    for _ in range(12):
        if f.exists() and f.stat().st_size > 0:
            break
        await asyncio.sleep(0.3)
    if not f.exists():
        return None, "sin archivo"
    txt = f.read_text(encoding="utf-8", errors="replace")
    return re.findall(r"<Button>(\d+)</Button>", txt), None


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for etiqueta, cmd in ENSAYOS:
            if cmd:
                await ma2.cmd("cd /")
                await ma2.cmd(cmd)
            botones, err = await exportar(ma2)
            print(f"  {etiqueta:<24} -> {botones}   err={err}")


if __name__ == "__main__":
    asyncio.run(main())
