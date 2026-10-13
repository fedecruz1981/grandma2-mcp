r"""
Lee los atributos reales de los Par COB II (fx32-34) para saber como
escribirles el DIM. Solo lectura: `list attribute`.

Uso: python scripts\probe_cob.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for fx in (32, 33, 34):
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"cd Fixture {fx}")
            p = r.prompt
            r = await ma2.cmd("list attribute")
            print("=" * 70)
            print(f"FIXTURE {fx}   prompt: {p!r}   err={r.errors}")
            n = 0
            for ln in r.body:
                if ln.strip():
                    print("   ", ln.strip()[:130])
                    n += 1
                if n > 40:
                    print("    ... (truncado)")
                    break


if __name__ == "__main__":
    asyncio.run(main())
