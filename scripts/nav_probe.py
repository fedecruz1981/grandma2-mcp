"""
Sondeo: singular vs plural en la navegacion de secuencias.

Hallazgo: `cd Sequences 137` NO entra a la secuencia; "Sequences" (plural) es
la pagina del pool. El objeto es `Sequence N` (singular). Ademas el pool
reporta 155 secuencias, no 153.

Solo lectura (cd / list).
Uso: python scripts/nav_probe.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

PRUEBAS = [
    "cd Sequences",
    "cd Sequence 137",
    "cd Sequence 137 Cue 1",
    "cd Sequence 156",
    "cd Sequence 155",
    "cd Sequence 1",
    "cd Sequence 137 Cue 1 Fixture 23",
    "cd Sequences",
    "list Sequence 1",
]


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()!r}\n")
        for c in PRUEBAS:
            r = await ma2.cmd(c)
            print("=" * 78)
            print(f">>> {c}")
            print(f"    prompt: {r.prompt!r}")
            if r.errors:
                print(f"    ERRORES: {r.errors}")
            cuerpo = [x for x in r.body if x.strip()]
            for ln in cuerpo[:10]:
                print(f"      {ln[:165]}")
            if not cuerpo and not r.errors:
                print("      (vacio)")


if __name__ == "__main__":
    asyncio.run(main())
