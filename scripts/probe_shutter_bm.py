"""
Por que: al importar el diseno nuevo, el strobo ef6 sobre SHUTTER en el grupo
BM (fx15-22, Nebula Max 162) se pierde: el export no trae ningun CueData de
SHUTTER para esos fixtures. El mismo ef6 en FRONT (fx9-14) si queda.

Este probe averigua cual es el nombre real del atributo de shutter de cada tipo
y si el efecto se puede escribir sobre el.

No modifica el show: solo lista atributos. Para probar escrituras usar
--escribir, que ademas borra al final lo que escribio.

Uso:
    python scripts/probe_shutter_bm.py
    python scripts/probe_shutter_bm.py --escribir
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

# un Par COB por tipo: 14 = FRONT (funciona), 15 = BM (falla), 23 = BF,
# 5 = BT, 1 = CM, 9 = FRONT
MUESTRAS = [
    (1, "CM  beamer 250 mini"),
    (5, "BT  stromber"),
    (9, "FRONT nebula flat 210"),
    (15, "BM  nebula max 162"),
    (23, "BF  protones chico"),
    (31, "blinder"),
]
ATTR_RE = re.compile(r"^Attribute\s+(\d+)\s+(\S+)")


async def main():
    escribir = "--escribir" in sys.argv
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()}\n")
        for fx, etiqueta in MUESTRAS:
            r = await ma2.cmd(f"cd Fixture {fx}")
            tipo = r.prompt.strip()
            r2 = await ma2.cmd("list attribute")
            filas = []
            for ln in r2.lines:
                m = ATTR_RE.match(ln.strip())
                if not m:
                    continue
                toks = ln.split()
                flag = next((t for i, t in enumerate(toks)
                             if t in ("On", "Off") and i > 2), "")
                filas.append((int(m.group(1)), m.group(2), flag))
            print(f"fx{fx:<3} {etiqueta:<26} {tipo}")
            for num, nombre, flag in filas:
                if re.search(r"SHUT|DIM|PAN|TILT", nombre):
                    print(f"      {num:>2} {nombre:<12} {flag}")
            for e in r2.errors:
                print(f"      ERROR: {e}")
            print()

        if not escribir:
            print("(sin escrituras; pasar --escribir para probar At Effect 6)")
            return

        # --- prueba real: guardar un ef6 sobre SHUTTER en cada tipo y exportar
        seq = 900
        print("=" * 70)
        print(f"prueba de escritura en la secuencia scratch {seq}")
        print("=" * 70)
        await ma2.cmd("Clear")
        for fx, etiqueta in MUESTRAS:
            await ma2.cmd(f"At Effect 6 Fixture {fx}.1")
        r = await ma2.cmd("Store Sequence 1 Cue 1")
        for e in r.errors:
            print(f"  ERROR store: {e}")
        r = await ma2.cmd(f'Store Sequence {seq} Cue 1')
        for ln in [x for x in r.body if x.strip()][-3:]:
            print(f"  {ln.strip()[:120]}")
        r = await ma2.cmd("SaveShow /noconfirm")
        for ln in [x for x in r.body if x.strip()][:2]:
            print(f"  {ln.strip()[:120]}")


if __name__ == "__main__":
    asyncio.run(main())
