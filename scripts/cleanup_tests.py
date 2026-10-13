"""
Borra las secuencias creadas durante las pruebas de sintaxis.

Las pruebas crearon: 156, 160, 161, 162, 163 y 170-174. Hay que dejarlas
borradas para que el pool vuelva a 155 secuencias y no queden cues con
valores de prueba (R=11 G=22 B=33 DIM=44) en el show.

Verifica al final que el pool tenga de nuevo 155 secuencias.
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

A_BORRAR = [156, 160, 161, 162, 163, 170, 171, 172, 173, 174]


def conteo(body):
    for ln in body:
        m = re.search(r"SequencePool\s+\d+\s+\w*\s*\((\d+)\)", ln)
        if m:
            return int(m.group(1))
    return None


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()

        await ma2.cmd("cd /")
        r = await ma2.cmd("list")
        print(f"pool ANTES : {conteo(r.body)}")

        for s in A_BORRAR:
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"Delete Sequence {s}")
            estado = "borrada" if not r.errors else f"ERROR {r.errors}"
            print(f"  Delete Sequence {s:<4} -> {estado}")

        await ma2.cmd("cd /")
        r = await ma2.cmd("list")
        despues = conteo(r.body)
        print(f"pool DESPUES: {despues}")

        # confirmar que no queda ninguna
        print("\nverificando que las borradas ya no existen:")
        for s in A_BORRAR:
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"cd Sequence {s}")
            existe = "AUN EXISTE" if not r.errors else "no existe"
            print(f"  Sequence {s:<4} -> {existe}")


if __name__ == "__main__":
    asyncio.run(main())
