"""
Sondeo de solo lectura: pool de Effects completo, Gels, y sintaxis de Assign.

Contexto: se confirmo que el pool de Effects existe y es legible (23 efectos,
incluidos Dimmer PWM / Dimmer Chase / Tilt Sin Pan stomp). Falta:
  1. la lista completa (la anterior se corto en 21 de 23)
  2. que hay en Gels (los cabezales usan COLOR1, que puede ser un gel)
  3. la sintaxis real de `Assign`, que `help` no documenta ("Syntax:Assign")

No escribe nada.
Uso: python scripts/assign_probe.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402)

POOLS = [
    "List Effect",
    "List EffectLibrary",
    "List EffectLibrary 1",
    "List Gel",
    "List Gels",
    "List PresetType Color",
]

SINTAXIS = [
    "Assign ?",
    "Assign Effect ?",
    "Assign Effect 1 ?",
    "help Assign",
    "help Assign Effect",
    "help EffectLibrary",
    "ListEffectLibrary ?",
    "ListEffectLibrary 1 ?",
]


def mostrar(r, maximo=40):
    if r.errors:
        print(f"    ERRORES: {r.errors}")
    cuerpo = [ln for ln in r.body if ln.strip()]
    for ln in cuerpo[:maximo]:
        print(f"      {ln}")
    if len(cuerpo) > maximo:
        print(f"      ... (+{len(cuerpo) - maximo} lineas)")
    if not cuerpo and not r.errors:
        print("      (vacio)")


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()}\n")
        print("#" * 78)
        print("# POOLS")
        for c in POOLS:
            r = await ma2.cmd(c)
            print("=" * 78)
            print(f">>> {c}")
            mostrar(r)

        print("\n" + "#" * 78)
        print("# SINTAXIS (solo pide ayuda, no ejecuta)")
        for c in SINTAXIS:
            r = await ma2.cmd(c)
            print("=" * 78)
            print(f">>> {c}")
            print(f"    prompt: {r.prompt}")
            mostrar(r, maximo=25)


if __name__ == "__main__":
    asyncio.run(main())
