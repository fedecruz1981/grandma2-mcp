"""
Por que los cabezales (fx1-4, Beamer 250 Mini) no se encienden aunque el DIM
este grabado en los 53 cues.

Verificado ya: el DIM de fx1-4 SI esta en el show (70/40/100/60... ninguno en 0).
Entonces si la lampara no prende, la causa esta fuera de las secuencias. Este
script revisa, en este orden, las causas clasicas de "la secuencia esta bien pero
no sale luz":

  1. Grand Master / Shutter Master en 0
  2. La capa (layer) donde estan los fixtures esta apagada
  3. Los fixtures no estan asignados a ninguna salida del LiveSetup
  4. Los propios fixtures estan apagados en el LiveSetup (no el Live)
  5. Hay un efecto encendido en el Live que los_override

No modifica nada. Solo lectura.

Uso: python scripts/diag_cabezales.py
"""
import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402

CABEZALES = (1, 2, 3, 4)


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ma2.cmd("cd /")
        print("=" * 72)
        print("1. GRAND MASTERS")
        print("=" * 72)
        for etiqueta, cmd in (("Grand Master 1-2", "Grandmaster 1"),
                              ("Grand Master 3-4", "Grandmaster 2")):
            r = await ma2.cmd(f"{cmd} at")
            print(f"  {etiqueta}: {cmd} at")
            for ln in [x for x in r.lines if x.strip()][:6]:
                print(f"      {ln.strip()[:100]}")
            if r.errors:
                print(f"      ERROR: {r.errors}")

        print()
        print("=" * 72)
        print("2. CAPAS (layers) - cual capa tiene los cabezales y si esta on")
        print("=" * 72)
        await ma2.cmd("cd /")
        r = await ma2.cmd("list layers")
        print(f"  comando: list layers   -> {len([x for x in r.lines if x.strip()])} lineas")
        for ln in [x for x in r.lines if x.strip()][:40]:
            print(f"      {ln.strip()[:100]}")
        for e in r.errors:
            print(f"      ERROR: {e}")

        print()
        print("=" * 72)
        print("3. LIVE SETUP - donde esta cada cabezal (layer, universo, direccion)")
        print("=" * 72)
        await ma2.cmd("cd /")
        r = await ma2.cmd("list live_setup")
        print("  comando: list live_setup")
        for ln in [x for x in r.lines if x.strip()][:30]:
            print(f"      {ln.strip()[:110]}")
        for e in r.errors:
            print(f"      ERROR: {e}")

        print()
        print("=" * 72)
        print("4. CAPA ASIGNADA A CADA CABEZAL, y si esa capa esta encendida")
        print("=" * 72)
        for fx in CABEZALES:
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"Fixture {fx}")
            for ln in [x for x in r.lines if x.strip()][:4]:
                print(f"  fx{fx}: {ln.strip()[:110]}")

        print()
        print("=" * 72)
        print("5. ESTADO LIVE de fx1 (DIM y SHUTTER ahora, no de la secuencia)")
        print("=" * 72)
        await ma2.cmd("cd /")
        await ma2.cmd("Fixture 1 At 0")
        await ma2.cmd("cd /")
        r = await ma2.cmd("list attribute")
        for ln in r.lines:
            s = ln.strip()
            if s.startswith("Attribute  1 ") or s.startswith("Attribute 18 ") \
                    or " Shutter " in s or s.startswith("Attribute  1 "):
                print(f"      {s[:150]}")
        await ma2.cmd("cd /")
        await ma2.cmd("Clear")


if __name__ == "__main__":
    asyncio.run(main())
