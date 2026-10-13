"""
Ejecuta comandos sueltos por telnet directo e imprime todo crudo.

Herramienta de exploracion: uso general sin editar el archivo.
Uso: python scripts/ma2_run.py "list /?" "export /?" "info /?"
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from ma2_telnet import Ma2


async def main():
    cmds = sys.argv[1:]
    if not cmds:
        print("falta un comando")
        return
    async with Ma2() as ma2:
        for c in cmds:
            r = await ma2.cmd(c)
            print("=" * 74)
            print(f"$ {c}")
            print(f"  prompt: {r.prompt}")
            print("-" * 74)
            for ln in r.lines:
                print("  ", ln)
            print()


if __name__ == "__main__":
    asyncio.run(main())