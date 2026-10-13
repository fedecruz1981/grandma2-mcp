r"""Cambia la funcion del boton 3.101 a Flash (12302), como el de HUMO 3.111.

No toca la secuencia 156: solo la funcion del boton.
Uso: python scripts\asignar_flash_101.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402


async def main():
    async with Ma2() as m:
        await m.at_prompt()
        r = await m.cmd("cd /")
        print(f">>> cd /   err={r.errors}")
        r = await m.cmd("Assign Flash At Executor 3.101")
        print(f">>> Assign Flash At Executor 3.101   err={r.errors}")
        for ln in r.lines:
            print(f"    {ln}")
        r = await m.cmd("SaveShow /noconfirm")
        print(f">>> SaveShow /noconfirm   err={r.errors}")
        for ln in r.lines:
            print(f"    {ln}")


if __name__ == "__main__":
    asyncio.run(main())
