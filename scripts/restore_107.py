r"""
Deshace el reemplazo accidental: el 3.107 tenia "DIMER FA" y le puse HUMO.
Restaura DIMER FA en el 3.107 y lista que hay en la Page 3 para elegir libres.

Uso: python scripts\restore_107.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

PAGE = 3


def num_de(prompt):
    m = re.search(r"(\d+)\s*>$", prompt or "")
    return int(m.group(1)) if m else None


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()

        await ma2.cmd("cd /")
        p = await ma2.cmd('cd Sequence "DIMER FA"')
        seq_fa = num_de(p.prompt)
        print(f"  DIMER FA = secuencia {seq_fa}  (prompt={p.prompt!r})")

        print("\n  executors Page 3:")
        for btn in range(101, 122):
            await ma2.cmd("cd /")
            q = await ma2.cmd(f"cd Executor {PAGE}.{btn}")
            print(f"    3.{btn}: {q.prompt!r}")

        if seq_fa:
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"Assign Sequence {seq_fa} Executor {PAGE}.107")
            print(f"\n  restaurar DIMER FA (seq {seq_fa}) en 3.107: "
                  f"{'ok' if not r.errors else 'ERR ' + str(r.errors)}")
            await ma2.cmd("cd /")
            q = await ma2.cmd(f"cd Executor {PAGE}.107")
            print(f"  3.107 ahora: {q.prompt!r}")
            await ma2.cmd("cd /")
            await ma2.cmd("SaveShow /noconfirm")
            print("  show guardado")


if __name__ == "__main__":
    asyncio.run(main())
