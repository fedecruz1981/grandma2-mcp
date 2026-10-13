"""
Compara que atributos tiene ACTIVOS cada tipo de fixture.

Por que: `list attribute` dentro de un fixture devuelve los 41 atributos
universales, con una columna "Universal" que marca On/Off. La pregunta es si
ese On/Off refleja el TIPO de fixture (y por lo tanto si los cabezales
tienen RGB) o es la misma lista para todos.

Uso: python scripts/attr_probe.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

MUESTRAS = [
    (1, "CM beamer 250 mini"),
    (5, "BT stromber"),
    (9, "flat 210"),
    (15, "BM nebula max 162"),
    (23, "BF protones"),
    (30, "BF protones (el otro)"),
    (31, "blinder"),
    (32, "par cob II"),
]

ATTR_RE = re.compile(r"^Attribute\s+(\d+)\s+(\S+)")


def parse(resp):
    """[(num, nombre, on_off), ...] de una respuesta de `list attribute`."""
    out = []
    for ln in resp.lines:
        m = ATTR_RE.match(ln.strip())
        if not m:
            continue
        toks = ln.split()
        flag = ""
        for i, t in enumerate(toks):
            if t in ("On", "Off") and i > 2:
                flag = t
                break
        out.append((int(m.group(1)), m.group(2), flag))
    return out


async def main():
    async with Ma2() as ma2:
        print(f"prompt inicial: {await ma2.at_prompt()}\n")
        tabla = {}
        for fx, etiqueta in MUESTRAS:
            r = await ma2.cmd(f"cd Fixture {fx}")
            tipo = r.prompt.strip()
            r2 = await ma2.cmd("list attribute")
            filas = parse(r2)
            encendidos = {n for _, n, f in filas if f == "On"}
            tabla[fx] = (etiqueta, tipo, encendidos, filas)
            print(f"fx{fx:<3} {etiqueta:<24} {len(encendidos)} On de {len(filas)}")
            print(f"      tipo: {tipo}")
            print(f"      On  : {sorted(encendidos)}")
            for e in r2.errors:
                print(f"      ERROR: {e}")
            print()

        # diferencias entre tipos
        print("=" * 78)
        print("diferencias de atributos On entre tipos:")
        base_fx = 1
        base = tabla[base_fx][2]
        for fx, (etiqueta, _, ons, _) in tabla.items():
            if fx == base_fx:
                continue
            extra = ons - base
            falta = base - ons
            if extra or falta:
                print(f"  fx{fx} ({etiqueta}):")
                if extra:
                    print(f"      On solo aca: {sorted(extra)}")
                if falta:
                    print(f"      On en fx{base_fx} pero no aca: {sorted(falta)}")
            else:
                print(f"  fx{fx} ({etiqueta}): identico a fx{base_fx}")

        # los RGB, specifically
        print("\n" + "=" * 78)
        print("RGB (atributos 12,13,14,15,16) por fixture:")
        for fx, (etiqueta, _, _, filas) in tabla.items():
            rgb = {n: f for num, n, f in filas if n.startswith("COLORRGB")}
            print(f"  fx{fx:<3} {etiqueta:<24} {rgb}")


if __name__ == "__main__":
    asyncio.run(main())
