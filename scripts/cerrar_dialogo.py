r"""
Cierra el dialogo modal "Overwrite Confirmation" que tiene la consola colgada.

Sintoma: todo comando responde `Invalid Key` y el prompt queda en `[Macro]>`.
Causa: hay una pregunta de sobrescritura esperando respuesta:

    Warning : There already exists a file with this name "sequ_45_lampara_beam.xml". :
    [1]: Overwrite
    [2]: Cancel

Mientras esa pregunta esta abierta, la linea de comandos no procesa nada.

Este script responde SIEMPRE `2` = Cancel. Nunca `1` = Overwrite: ese archivo
ya existe y no tenemos por que pisarlo para destrabar la consola. Si el
dialogo fuera otro distinto, cancelarlo tambien es la accion segura.

Despues manda `Fixture 1` + `list attribute` y mira si vuelve a responder,
que es la senal de que la consola quedo utilizable.

Uso: python scripts\cerrar_dialogo.py
"""
import asyncio
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402


def _respuesta(lineas):
    return "\n".join(f"      {ln}" for ln in lineas if ln.strip()) or "      (vacio)"


async def main():
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")
    print("respuesta al dialogo: 2 (Cancel) -- no pisa ningun archivo")

    async with Ma2() as ma2:
        # Estado inicial: que hay esperando
        await ma2.drain()
        print()
        print("=" * 74)
        print("1. ESTADO INICIAL (lo que hay colgado)")
        print("=" * 74)
        crudo = await ma2._read_until_prompt(max_wait=4.0)
        from ma2_telnet import ANSI  # noqa: E402
        texto = ANSI.sub("", crudo or "")
        for ln in texto.replace("\r", "\n").split("\n"):
            if ln.strip():
                print(f"      {ln.strip()[:112]}")
        if not texto.strip():
            print("      (nada pendiente al conectar)")

        # Mandar la respuesta del dialogo
        for intento, tecla in enumerate(("2", "2"), start=1):
            await ma2.drain()
            await ma2._raw(tecla)
            crudo = await ma2._read_until_prompt(max_wait=4.0)
            texto = ANSI.sub("", crudo or "")
            limpio = "\n".join(ln for ln in texto.replace("\r", "\n").split("\n")
                               if ln.strip())
            print()
            print(f"2. RESPONDI '{tecla}' (intento {intento})")
            print(_respuesta(limpio.split("\n")))
            if "Overwrite" not in limpio and "Cancel" not in limpio:
                print("      -> el dialogo ya no esta: cerrado")
                break
            if not limpio.strip():
                print("      -> silencio: dialogo consumido")
                break

        # Verificar que la consola responde de verdad
        print()
        print("=" * 74)
        print("3. VERIFICACION: responde la consola?")
        print("=" * 74)
        await ma2.drain()
        await ma2._raw("cd /")
        crudo = await ma2._read_until_prompt(max_wait=4.0)
        print(f"  >>> cd /")
        print(_respuesta(ANSI.sub("", crudo or "").replace("\r", "\n").split("\n")))

        await ma2.drain()
        await ma2._raw("Fixture 1")
        crudo = await ma2._read_until_prompt(max_wait=4.0)
        print(f"\n  >>> Fixture 1")
        print(_respuesta(ANSI.sub("", crudo or "").replace("\r", "\n").split("\n")))

        await ma2.drain()
        await ma2._raw("list attribute")
        crudo = await ma2._read_until_prompt(max_wait=5.0)
        lineas = ANSI.sub("", crudo or "").replace("\r", "\n").split("\n")
        print(f"\n  >>> list attribute   ({len([l for l in lineas if l.strip()])} lineas)")
        print(_respuesta(lineas[:12]))

        invalido = "Invalid Key" in "".join(lineas)
        print()
        if invalido:
            print("  AUN RESPONDE 'Invalid Key': hay otro dialogo abierto.")
            print("  hay que mirarlo a mano en la consola.")
        else:
            print("  OK: la consola vuelve a responder comandos.")

        await ma2.drain()
        await ma2._raw("Clear")


if __name__ == "__main__":
    asyncio.run(main())