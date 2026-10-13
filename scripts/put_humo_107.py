r"""
Recupera el boton HUMO: reasigna la secuencia 20 (HUMO) al executor 3.107.

La secuencia 20 sobrevivio al reemplazo de executor (solo quedo sin boton).
Antes de asignar se mira que hay en 3.107 y que contiene la secuencia 20.

Uso: python scripts\put_humo_107.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
SEQ = 20
PAGE, BTN = 3, 107


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()

        # que hay hoy en el 3.107
        await ma2.cmd("cd /")
        p = await ma2.cmd(f"cd Executor {PAGE}.{BTN}")
        print(f"  3.{BTN} antes:  prompt={p.prompt!r}")

        # contenido de la secuencia HUMO
        await ma2.cmd("cd /")
        p = await ma2.cmd(f"cd Sequence {SEQ}")
        print(f"  seq {SEQ}:       prompt={p.prompt!r}")
        await ma2.cmd("cd /")
        await ma2.cmd(f'Export Sequence {SEQ} "humo20"')
        for _ in range(10):
            f = EXPORT_DIR / "humo20.xml"
            if f.exists() and f.stat().st_size > 0:
                break
            await asyncio.sleep(0.3)
        if f.exists():
            txt = f.read_text(encoding="utf-8", errors="replace")
            import re
            nums = re.findall(r'<Number number="([^"]+)"', txt)
            print(f"  seq {SEQ} tiene {len(nums)} cues: {nums[:12]}")
            ef = re.findall(r'<Effect name="([^"]+)"', txt)
            if ef:
                from collections import Counter
                print(f"    effects: {Counter(ef).most_common()}")
            vals = re.findall(r'attribute_name="([^"]+)"[^>]*/>\s*<Value>([^<]*)',
                              txt)
            from collections import Counter
            if vals:
                print(f"    atributos: {Counter(a for a, _ in vals).most_common()}"
                      f"  valores={sorted(set(v for _, v in vals))[:10]}")

        # asignar
        await ma2.cmd("cd /")
        r = await ma2.cmd(f"Assign Sequence {SEQ} Executor {PAGE}.{BTN}")
        print(f"  asignar seq {SEQ} -> 3.{BTN}: "
              f"{'ok' if not r.errors else 'ERR ' + str(r.errors)}")
        await ma2.cmd("cd /")
        p = await ma2.cmd(f"cd Executor {PAGE}.{BTN}")
        print(f"  3.{BTN} despues: prompt={p.prompt!r}")

        await ma2.cmd("cd /")
        r = await ma2.cmd("SaveShow /noconfirm")
        for ln in [x for x in r.body if x.strip()][:2]:
            print(f"  {ln.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
