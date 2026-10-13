r"""
Exporta una secuencia a XML para inspeccionarla.

Uso: python scripts\export_seq.py <n> [nombre]
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")


async def main():
    seq = sys.argv[1]
    nombre = sys.argv[2] if len(sys.argv) > 2 else f"chk_live_{seq}"
    f = EXPORT_DIR / f"{nombre}.xml"
    if f.exists():
        f.unlink()
    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ma2.cmd("cd /")
        r = await ma2.cmd(f'Export Sequence {seq} "{nombre}"')
        print(f"Export Sequence {seq}: err={r.errors}")
        for _ in range(20):
            if f.exists() and f.stat().st_size > 0:
                break
            await asyncio.sleep(0.3)
    if f.exists():
        print(f"escrito: {f} ({f.stat().st_size} bytes)")
    else:
        print("no se creo el archivo")


if __name__ == "__main__":
    asyncio.run(main())
