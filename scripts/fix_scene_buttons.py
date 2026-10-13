r"""
Corrige la funcion de boton de las escenas 3.101-3.106 a Go.

Al reasignar las secuencias se heredo la funcion de boton vieja:
  3.101-3.105 = Toggle (12307)  y  3.106 = Flash (12302)
Para una lista de cues lo correcto es Go (12299): cada pulsacion avanza el cue.
HUMO (3.111) se deja como el original: Flash (12302).

Uso: python scripts\fix_scene_buttons.py [--solo-ver]
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
CODIGOS = {"12290": "Off", "12291": "Temp", "12293": "On", "12299": "Go",
           "12302": "Flash", "12306": "Swop", "12307": "Toggle"}
BOTONES = [101, 102, 103, 104, 105, 106]


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
    b = re.findall(r"<Button>(\d+)</Button>", txt)
    return b


async def main():
    solo_ver = "--solo-ver" in sys.argv
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for btn in BOTONES:
            ex = f"3.{btn}"
            antes = await botones(ma2, ex)
            cod = antes[0] if antes else "?"
            if not solo_ver:
                await ma2.cmd("cd /")
                r = await ma2.cmd(f"Assign Go At Executor {ex}")
                if r.errors:
                    print(f"  3.{btn}: ERROR {r.errors}")
                    continue
                ahora = await botones(ma2, ex)
                cod2 = ahora[0] if ahora else "?"
                print(f"  3.{btn}: {cod} ({CODIGOS.get(cod, '?')})"
                      f" -> {cod2} ({CODIGOS.get(cod2, '?')})")
            else:
                print(f"  3.{btn}: {cod} ({CODIGOS.get(cod, '?')})")

        print(f"\n  HUMO 3.111: "
              f"{[c for c in (await botones(ma2, '3.111') or [])][:1]}"
              " (12302 = Flash)")

        if not solo_ver:
            await ma2.cmd("cd /")
            await ma2.cmd("SaveShow /noconfirm")
            print("  show guardado")


if __name__ == "__main__":
    asyncio.run(main())
