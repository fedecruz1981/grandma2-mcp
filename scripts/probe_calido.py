r"""
Exporta el preset de color CALIDO (4.18) para ver que atributos y valores
le corresponden a los Par COB II (fx32-34). Solo lectura.

Uso: python scripts\probe_calido.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")


async def main():
    f = EXPORT_DIR / "preset_calido.xml"
    async with Ma2() as ma2:
        await ma2.at_prompt()
        if f.exists():
            f.unlink()
        await ma2.cmd("cd /")
        r = await ma2.cmd('Export Preset 4.18 "preset_calido"')
        print(f">>> Export Preset 4.18   err={r.errors}")
        for _ in range(15):
            if f.exists() and f.stat().st_size > 0:
                break
            await asyncio.sleep(0.3)
        if not f.exists():
            print("    no se creo el archivo")
            return
        txt = f.read_text(encoding="utf-8", errors="replace")
        print(f"    {f.name}: {len(txt)} chars")
        print("=" * 70)
        print(txt)


if __name__ == "__main__":
    asyncio.run(main())
