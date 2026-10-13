r"""
Intenta leer la funcion del boton del executor HUMO exportando a XML.

`List Executor` no expone la button function. Se prueba Export Executor y
Export ExecutorPage: si el XML incluye "toggle"/"button", queda verificado.

Uso: python scripts\export_exec.py
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
    ("exec111", 'Export Executor 3.111 "exec111"'),
    ("page3", 'Export ExecutorPage 3 "page3"'),
]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for nombre, cmd in ENSAYOS:
            f = EXPORT_DIR / f"{nombre}.xml"
            if f.exists():
                f.unlink()
            await ma2.cmd("cd /")
            r = await ma2.cmd(cmd)
            print(f">>> {cmd}   err={r.errors}")
            for _ in range(12):
                if f.exists() and f.stat().st_size > 0:
                    break
                await asyncio.sleep(0.3)
            if not f.exists():
                print("    no se creo el archivo")
                continue
            txt = f.read_text(encoding="utf-8", errors="replace")
            print(f"    {f.name}: {len(txt)} chars")
            for pat in ("oggle", "emp", "Button", "Function"):
                for m in re.finditer(pat, txt):
                    s, e = max(0, m.start() - 120), min(len(txt), m.end() + 160)
                    frag = txt[s:e].replace("\n", " ").replace("\r", " ")
                    print(f"      [{pat}] ...{frag}...")
                    break


if __name__ == "__main__":
    asyncio.run(main())
