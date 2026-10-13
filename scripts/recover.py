"""Saca a la consola del dialogo de Overwrite Confirmation que quedo abierto.

El Import sobre una secuencia existente abre:
    Overwrite Confirmation : ... object "Sequ 191" :
    [1]: Overwrite   2: Overwrite|All   3: Insert   4: Insert|All   5: Cancel

Hay que contestar con un numero. Se manda "5" (Cancel) y se verifica el prompt.
Uso: python scripts\\recover.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402


async def main():
    async with Ma2() as ma2:
        await asyncio.sleep(0.5)
        for intento, tecla in enumerate(["5", "1", "5"]):
            print(f"--- intento {intento}: enviando {tecla!r}")
            r = await ma2.cmd(tecla)
            print(f"    prompt={r.prompt!r} err={r.errors}")
            for ln in [x for x in r.body if x.strip()][:6]:
                print(f"    {ln.strip()[:120]}")
            if r.prompt and "Macro" in r.prompt:
                break
        r = await ma2.cmd("cd /")
        print(f"\n  prompt final={r.prompt!r}")


if __name__ == "__main__":
    asyncio.run(main())
