r"""
Mide el RANGO real de PAN y TILT en los cabezales antes de escribir nada.

Por que hay que medir: el usuario pide "10 de pan y tilt". Pero en grandMA2 un
valor de atributo es una posicion ABSOLUTA, no un desplazamiento. Si no se sabe
que escala usa el Beamer 250 Mini (0-255, 0-360, -180..180) y cual es su
centro, escribir "10" puede dejar el haz apuntando al piso o al cielo.

Este script solo LEE. No escribe ningun valor en el show.

Intenta varias sintaxis de telnet para sacar el min/max/default del atributo:
  Fixture 1 Attribute 3 / At 0 / At 100 / Print / Dump
y de paso mira si algun valor de PAN/TILT quedo guardado en otra secuencia del
show (por ejemplo la 45, "lampora beam"), que serviria para calibrar.

Uso: python scripts\sondar_pan_tilt.py
"""
import asyncio
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402
from ma2_telnet import ANSI  # noqa: E402

EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")


async def mandar(ma2, cmd, espera=3.5):
    await ma2.drain()
    await ma2._raw(cmd)
    crudo = await ma2._read_until_prompt(max_wait=espera)
    txt = ANSI.sub("", crudo or "")
    lineas = [x.strip() for x in txt.replace("\r", "\n").split("\n") if x.strip()]
    if any("Overwrite" in x for x in lineas):
        await ma2.drain()
        await ma2._raw("2")
        await ma2._read_until_prompt(max_wait=3.0)
        return ["(respondido 2 = Cancel a un dialogo de Overwrite)"]
    return lineas


async def main():
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")
    async with Ma2() as ma2:
        # ---------------------------------------------------------------
        print("=" * 76)
        print("1. RANGO DE LOS ATRIBUTOS DE fx1 (PAN=3, TILT=4)")
        print("=" * 76)
        intentos = [
            "Fixture 1",
            "Fixture 1 Attribute 3",
            "Fixture 1 At 0",
            "Fixture 1 At 100",
            "Attribute 3",
            "at 0",
        ]
        for cmd in intentos:
            await mandar(ma2, "cd /")
            lineas = await mandar(ma2, cmd)
            print(f"\n  >>> {cmd}")
            for ln in lineas[:14]:
                print(f"      {ln[:114]}")

        # ---------------------------------------------------------------
        print()
        print("=" * 76)
        print("2. PAN/TILT: LA CONSOLA MUESTRA ALGO AL MOVER EL ENCODER?")
        print("=" * 76)
        # Grandmaster/fixture sheet: probar que la consola responda con numeros
        for cmd in ("Fixture 1 At 0.0", "Fixture 1 At 360", "Fixture 1 At -180",
                    "Fixture 1 At 255"):
            await mandar(ma2, "cd /")
            lineas = await mandar(ma2, cmd)
            print(f"\n  >>> {cmd}")
            for ln in lineas[:8]:
                print(f"      {ln[:114]}")

        # ---------------------------------------------------------------
        print()
        print("=" * 76)
        print("3. ALGUNA SECUENCIA DEL SHOW YA TIENE PAN/TILT? (escala real)")
        print("=" * 76)
        sello = int(time.time()) % 100000
        for seq in (45, 1, 156):
            tag = f"pt_{seq}_{sello}"
            f = EXPORT / f"{tag}.xml"
            f.unlink(missing_ok=True)
            await mandar(ma2, "cd /")
            await mandar(ma2, f"Export Sequence {seq} '{tag}'")
            for _ in range(24):
                if f.exists() and f.stat().st_size > 0:
                    break
                await asyncio.sleep(0.3)
            if not (f.exists() and f.stat().st_size > 0):
                print(f"\n  seq {seq}: no se pudo exportar")
                continue
            txt = f.read_text(encoding="utf-8", errors="replace")
            f.unlink(missing_ok=True)
            panes = re.findall(r'attribute_name="(?:PAN|TILT)"[^>]*>\s*'
                               r'<Value>([^<]*)</Value>', txt)
            dim = re.findall(r'attribute_name="DIM"[^>]*>\s*<Value>([^<]*)</Value>',
                             txt)
            print(f"\n  seq {seq}: {len(panes)} valores PAN/TILT, "
                  f"{len(dim)} valores DIM")
            if panes:
                print(f"      PAN/TILT encontrados: {sorted(set(panes))[:12]}")
            else:
                print("      (ningun PAN/TILT guardado -> no hay escala que "
                      "tomar de aca)")

        await mandar(ma2, "cd / Clear")


if __name__ == "__main__":
    asyncio.run(main())