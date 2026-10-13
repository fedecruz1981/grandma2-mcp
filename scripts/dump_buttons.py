r"""
Compara la funcion de boton (<Button> codigo) de varios executors.

Sirve para saber que codigo corresponde a Go, Toggle, Temp, etc., comparando
el HUMO (que pusimos en Toggle) contra botones conocidos.

Uso: python scripts\dump_buttons.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")

EXECUTORS = [3.101, 3.102, 3.107, 3.108, 3.109, 3.110, 3.111,
             3.112, 3.113, 3.114]


async def sacar(ma2, ex):
    f = EXPORT_DIR / "btnprobe.xml"
    if f.exists():
        f.unlink()
    await ma2.cmd("cd /")
    r = await ma2.cmd(f'Export Executor {ex} "btnprobe"')
    if r.errors:
        return None, None
    for _ in range(12):
        if f.exists() and f.stat().st_size > 0:
            break
        await asyncio.sleep(0.3)
    if not f.exists():
        return None, None
    txt = f.read_text(encoding="utf-8", errors="replace")
    nombre = re.search(r'name="([^"]*)"', txt)
    botones = re.findall(r"<Button>(\d+)</Button>", txt)
    return (nombre.group(1) if nombre else "?"), botones


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for ex in EXECUTORS:
            nombre, botones = await sacar(ma2, ex)
            pagina, btn = str(ex).split(".")
            print(f"  3.{btn:>3}  {str(nombre):<28} Buttons={botones}")


if __name__ == "__main__":
    asyncio.run(main())
