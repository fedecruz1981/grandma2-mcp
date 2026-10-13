"""
Encuentra la sintaxis que REALMENTE asigna una secuencia a un executor.

Sintoma: `cd Executor 3.101` + `Assign Sequence 156` responde "ok" y no hace
nada: el prompt del boton sigue diciendo `ARCO IRIS LED 3.101`. Es el mismo
tipo de no-op silencioso que `Assign Effect` (effect_test2.py).

READ-BACK: el prompt del executor es la unica fuente. Si el nombre del boton
cambia de `ARCO IRIS LED` a otro, la asignacion funciono. `List` en el
executor devuelve "NO OBJECTS FOUND FOR LIST", asi que no sirve.

Se prueban las variantes del vocabulario MA2 (Assign con y sin To, Executor,
ExecButton, Page). La 3.101 es el destino real que quiere el operador, asi
que si alguna funciona se aplica de verdad y no hay que tirar trabajo.

Tambien se prueba como VACIAR un executor, que es la otra mitad del pedido
("borra el show viejo solo esos executors").

Uso: python scripts\assign_probe2.py [secuencia]
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

SEQ = int(sys.argv[1]) if len(sys.argv) > 1 else 156
PAG, BOT = 3, 101
ANTES = "ARCO IRIS LED"


async def prompt_de(ma2, pag, bot):
    await ma2.cmd("cd /")
    r = await ma2.cmd(f"cd Executor {pag}.{bot}")
    return r.prompt


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        inicial = await prompt_de(ma2, PAG, BOT)
        print(f"prompt inicial: {inicial!r}")
        print(f"(si sale de '{ANTES}', la asignacion funciono)\n")

        VARIANTES = [
            # asignar secuencia 156 al boton 3.101
            f"Assign Sequence {SEQ} Executor {PAG} {BOT}",
            f"Assign Sequence {SEQ} To Executor {PAG}.{BOT}",
            f"Assign Sequence {SEQ} Executor {PAG}.{BOT}",
            f"Assign Sequence {SEQ} Page {PAG}.{BOT}",
            f"Assign Sequence {SEQ} ExecButton1 {BOT}",
            f"Assign {SEQ} Executor {PAG}.{BOT}",
            f"Assign Sequence {SEQ} 3.{BOT}",
        ]

        for v in VARIANTES:
            await ma2.cmd("cd /")
            await ma2.cmd(f"cd Executor {PAG}.{BOT}")
            r = await ma2.cmd(v)
            await ma2.cmd("cd /")
            p = await prompt_de(ma2, PAG, BOT)
            cambio = "CAMBIO ***" if p != inicial else "sin cambio"
            print(f"  {v:<48} "
                  f"{'ok' if not r.errors else 'ERR'}  {cambio}")
            print(f"      prompt ahora: {p!r}")
            if r.errors:
                for ln in [x for x in r.body if x.strip()][:3]:
                    print(f"        {ln.strip()[:130]}")
            if p != inicial:
                print("\n  *** ENCONTRADA. Saliendo para no seguir probando "
                      "sobre el boton real ***")
                break

        print("\n--- como vaciar un executor ---")
        VACIAR = ["Assign None", "Remove", "Clear", "Assign Sequence 0",
                  "Off", "Assign Empty Sequence 0"]
        for v in VACIAR:
            await ma2.cmd("cd /")
            await ma2.cmd(f"cd Executor {PAG}.{BOT}")
            r = await ma2.cmd(v)
            await ma2.cmd("cd /")
            p = await prompt_de(ma2, PAG, BOT)
            print(f"  {v:<28} {'ok' if not r.errors else 'ERR'}  "
                  f"prompt={p!r}")


if __name__ == "__main__":
    asyncio.run(main())