"""
Encuentra la sintaxis correcta para setear un atributo, usando el
Programmer como read-back (no escribe en el show).

Contexto: no existe el verbo `Create` en MA2, y `Store Cue N Sequence M`
necesita que la secuencia exista. Ademas hay que confirmar con que verbo se
escribe un valor de atributo (RGB) y como se selecciona un rango de fixtures.

Estrategia: seleccionar fixture, probar variantes de sintaxis del atributo, y
despues `cd Programmer` + `list` para LEER que quedo en el programador.
El Programmer es estado de la consola, no del show: se puede freely tocar.

Uso: python scripts/attr_syntax.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

# variantes para setear COLORRGB1 (atributo 12, ScreenName "R")
VARIANTES = [
    'Attribute "ColorRGB1" At 40',
    'Attribute ColorRGB1 At 41',
    'Attribute "R" At 42',
    'Attribute "COLORRGB1" At 43',
    'Attribute 12 At 44',
]


async def prog(ma2):
    """Vuelve al programador y lee el estado del fixture 23."""
    await ma2.cmd("cd Programmer 1")
    r = await ma2.cmd("list")
    return r


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()!r}\n")

        # 1) como se selecciona un fixture
        print("#" * 78)
        print("# SELECCION")
        for c in ["cd LiveSetup", "Fixture 23", "list",
                  "Fixture 23 Thru 30", "list"]:
            r = await ma2.cmd(c)
            print(f">>> {c}")
            print(f"    prompt={r.prompt!r}"
                  f"{'  ERR:' + str(r.errors) if r.errors else ''}")
            for ln in [x for x in r.body if x.strip()][:6]:
                print(f"      {ln[:150]}")
            print()

        # 2) sintaxis de atributo, leyendo el programador
        print("#" * 78)
        print("# SINTAXIS DE ATRIBUTO (read-back via Programmer)")
        await ma2.cmd("cd LiveSetup")
        await ma2.cmd("Fixture 23")
        for v in VARIANTES:
            r = await ma2.cmd(v)
            print(f">>> {v}")
            print(f"    prompt={r.prompt!r}"
                  f"{'  ERR:' + str(r.errors) if r.errors else '  (sin error)'}")
            p = await prog(ma2)
            for ln in [x for x in p.body if x.strip()][:4]:
                print(f"      prog| {ln[:150]}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
