r"""
Verifica el executor 3.103 tras re-importar la secuencia 158:
debe seguir apuntando a la 158 y con funcion Go.

Uso: python scripts\check_exec_103.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")


async def main():
    nombre = "exec103"
    f = EXPORT_DIR / f"{nombre}.xml"
    async with Ma2() as ma2:
        await ma2.at_prompt()
        if f.exists():
            f.unlink()
        await ma2.cmd("cd /")
        r = await ma2.cmd(f'Export Executor 3.103 "{nombre}"')
        print(f">>> Export Executor 3.103   err={r.errors}")
        for _ in range(12):
            if f.exists() and f.stat().st_size > 0:
                break
            await asyncio.sleep(0.3)
        if not f.exists():
            print("    no se creo el archivo")
            return
        txt = f.read_text(encoding="utf-8", errors="replace")
        print(f"    {f.name}: {len(txt)} chars")
        # lineas clave: nombre, secuencia, funcion de boton
        for pat in ("name=", "sequence", "Button", "Function", "Assign"):
            for m in re.finditer(pat, txt, re.I):
                s, e = max(0, m.start() - 100), min(len(txt), m.end() + 140)
                frag = txt[s:e].replace("\n", " ").replace("\r", " ")
                print(f"      [{pat}] ...{frag}...")
                break


if __name__ == "__main__":
    asyncio.run(main())
