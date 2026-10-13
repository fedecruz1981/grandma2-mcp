r"""
Confirma que Assign Sequence conserva la funcion de boton y deja HUMO en Flash.

El 3.106 (ex-HUMO) muestra 12302 = Flash: al reasignar la secuencia se heredo
la funcion del boton viejo. Se comprueba en un scratch, y se corrige HUMO
(3.111) a Flash, que es como era el original (apretar y mantener = humo).

Uso: python scripts\fix_humo_flash.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")


async def botones(ma2, ex):
    f = EXPORT_DIR / "sb.xml"
    if f.exists():
        f.unlink()
    await ma2.cmd("cd /")
    await ma2.cmd(f'Export Executor {ex} "sb"')
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

        print("  herencia en scratch 9.1:")
        await ma2.cmd("cd /")
        await ma2.cmd("Delete Executor 9.1")
        await ma2.cmd("cd /")
        await ma2.cmd("Assign Sequence 20 Executor 9.1")
        print(f"    recien asignado      -> {await botones(ma2, '9.1')}")
        await ma2.cmd("cd /")
        await ma2.cmd("Assign Flash At Executor 9.1")
        print(f"    puesto a Flash       -> {await botones(ma2, '9.1')}")
        await ma2.cmd("cd /")
        await ma2.cmd("Assign Sequence 20 Executor 9.1")
        print(f"    reasignada la seq    -> {await botones(ma2, '9.1')}"
              "   (si sigue 12302, hereda)")
        await ma2.cmd("cd /")
        await ma2.cmd("Delete Executor 9.1")

        print("\n  HUMO 3.111:")
        print(f"    antes                -> {await botones(ma2, '3.111')}")
        await ma2.cmd("cd /")
        r = await ma2.cmd("Assign Flash At Executor 3.111")
        print(f"    Assign Flash         -> {'ok' if not r.errors else r.errors}")
        print(f"    despues              -> {await botones(ma2, '3.111')}"
              "   (12302 = Flash)")

        await ma2.cmd("cd /")
        await ma2.cmd("SaveShow /noconfirm")
        print("\n  show guardado")


if __name__ == "__main__":
    asyncio.run(main())
