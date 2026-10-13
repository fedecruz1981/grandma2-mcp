"""
Sondeo de solo lectura: como se direccionan y desasignan button executors.

Contexto: el operador quiere las 6 escenas en 3.101..3.106 y borrar SOLO los
executors viejos de ahi (no tocar las 153 secuencias ni los demas botones).
Hay que confirmar la sintaxis de navegacion y de desasignacion antes de
escribir nada.

No modifica nada: solo cd / list / help.
Uso: python scripts/exec_probe.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

PRUEBAS = [
    "cd Executors 3.102",
    "list",
    "cd Executors 3.111",
    "list",
    "cd ButtonExecutor 3.102",
    "cd Executor 3.102",
    "help Assign",
    "list allbuttonexecutors 3.102",
    "cd Sequences 3.102",
]


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()}\n")
        for c in PRUEBAS:
            r = await ma2.cmd(c)
            print("=" * 78)
            print(f">>> {c}")
            print(f"    prompt: {r.prompt}")
            if r.errors:
                print(f"    ERRORES: {r.errors}")
            for ln in [x for x in r.body if x.strip()][:14]:
                print(f"      {ln[:150]}")


if __name__ == "__main__":
    asyncio.run(main())
