"""Diagnostico rapido: existe la 191?, que responde el Export?"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for c in ["cd /", "cd Sequence 191", "cd /",
                  'Export Sequence 191 "mo2"']:
            r = await ma2.cmd(c)
            print(f">>> {c}")
            print(f"    prompt={r.prompt!r}  errores={r.errors}")
            for ln in [x for x in r.body if x.strip()][:4]:
                print(f"    {ln.strip()[:130]}")
        p = EXPORT_DIR / "mo2.xml"
        print(f"\n  mo2.xml existe={p.exists()}"
              f"  {p.stat().st_size if p.exists() else ''}")
        if p.exists():
            print(p.read_text(encoding="utf-8")[:600])


if __name__ == "__main__":
    asyncio.run(main())
