"""
Lista de atributos por tipo de fixture (solo lectura).

Por que: el PDF usa instrucciones que dependen de atributos que yo no he
verificado. "Foco abierto" y "haz azul cerrado" (Q1/Q4 en CM) hablan de iris
o shutter; "azul cielo" (Q1 BT) es un color que no esta en mi paleta; "snap"
es una indicacion de tiempo de fade, no un valor.

Antes de traducir necesito saber que atributos existen de verdad en cada tipo,
para no inventar nombres. Ademas el listado viene del tipo de fixture, asi que
con 2 fixtures representativos por grupo alcanza.

Solo lectura: `list attribute`.
Uso: python scripts/attr_list.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

# un fixture representativo de cada grupo del rig
REPS = {
    1:  "CM    fx1-4   Beamer 250 Mini (cabezales)",
    5:  "BT    fx5-8   Stromber",
    9:  "FRONT fx9-14  Nebula Flat 210",
    15: "BM    fx15-22 Nebula Max 162",
    23: "BF    fx23-30 Protones chico",
}


async def main():
    out = []
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for fx in sorted(REPS):
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"cd Fixture {fx}")
            r = await ma2.cmd("list attribute")
            out.append("=" * 78)
            out.append(f"FIXTURE {fx}   {REPS[fx]}")
            out.append(f"  prompt: {r.prompt!r}")
            if r.errors:
                out.append(f"  ERRORES: {r.errors}")
            n = 0
            for ln in r.body:
                if ln.strip():
                    out.append(f"    {ln.strip()[:150]}")
                    n += 1
                if n > 60:
                    out.append("    ... (truncado)")
                    break
            out.append("")
    Path("data/_attrs.txt").write_text("\n".join(out), encoding="utf-8")
    print("escrito data/_attrs.txt")
    # resumen: que atributos de interes existen
    txt = "\n".join(out)
    for clave in ("DIM", "COLORRGB1", "COLORRGB2", "COLORRGB3",
                  "IRIS", "SHUTTER", "GOBIE", "PAN", "TILT", "ZOOM",
                  "FOCUS", "BEAM", "CTXO", "CTXF"):
        hits = len(re.findall(rf"\b{clave}\b", txt))
        if hits:
            print(f"  {clave:<10} aparece {hits} veces")


if __name__ == "__main__":
    asyncio.run(main())