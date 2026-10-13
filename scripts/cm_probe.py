r"""
Que atributos acepta de verdad cada grupo, medido grabando y exportando.

Por que existe: `list attribute` en LiveSetup devuelve el catalogo UNIVERSAL
de 41 atributos, identico en los 5 tipos de fixture (data/_attrs.txt), asi que
no sirve para saber que implementa cada cabezal. Y los comandos `Attribute`
contestan "ok" aunque el fixture descarte el valor (no-op silencioso), como
paso con COLORRGB1/2/3 en fx1-4.

Unico metodo fiable: Clear -> seleccionar -> Attribute "X" At V -> At 50 ->
Store Cue 1 Sequence N -> Export -> mirar el XML.

Metodo de esta prueba (aprendido de cm_final.py, que dio NO ENTRA hasta en el
control): UNA SECUENCIA DISTINTA POR CASO. Nunca `Delete` sobre una secuencia
que no existe: ese error rompia la cadena entera de comandos del caso.
Los controles positivos (fx5-8, fx23-30 con COLORRGB1) prueban que el metodo
anda; el control negativo (fx1-4 con COLORRGB1) confirma el descarte.

Uso: python scripts\cm_probe.py
"""
import asyncio
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
SEQ0 = 190

# (etiqueta, ini, fin, atributo)  -- valor fijo 55 para todos
CASOS = [
    ("CONTROL +", 5,  8,  "COLORRGB1"),
    ("CONTROL +", 23, 30, "COLORRGB1"),
    ("CONTROL -", 1,  4,  "COLORRGB1"),
    ("CM       ", 1,  4,  "COLOR1"),
    ("CM       ", 1,  4,  "COLORTEMPERATURE"),
    ("CM       ", 1,  4,  "SHUTTER"),
    ("CM       ", 1,  4,  "FOCUS"),
    ("CM       ", 1,  4,  "PAN"),
    ("CM       ", 1,  4,  "TILT"),
    ("CM       ", 1,  4,  "GOBO1"),
    ("CM       ", 1,  4,  "PRISMA1"),
    ("CM       ", 1,  4,  "FROST"),
    ("CM       ", 1,  4,  "COLORMIXER"),
]


def leer(tag):
    ruta = EXPORT_DIR / f"{tag}.xml"
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    out = []
    for cd in root.iter(f"{NS}CueData"):
        ch = cd.find(f"{NS}Channel")
        va = cd.find(f"{NS}Value")
        if ch is not None:
            out.append((int(ch.get("fixture_id")),
                        ch.get("attribute_name"),
                        va.text if va is not None else None))
    return out


async def main():
    creadas = []
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for i, (etiq, ini, fin, attr) in enumerate(CASOS):
            seq = SEQ0 + i
            tag = f"cmp{i}"
            sel = f"Fixture {ini}" if ini == fin else f"Fixture {ini} Thru {fin}"

            await ma2.cmd("cd /")
            await ma2.cmd("Clear")
            r1 = await ma2.cmd(sel)
            r2 = await ma2.cmd(f'Attribute "{attr}" At 55')
            await ma2.cmd("At 50")
            r3 = await ma2.cmd(f"Store Cue 1 Sequence {seq} /noconfirm")
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "{tag}"')
            creadas.append(seq)

            datos = leer(tag) or []
            # los fx involucrados
            fxs = {ini} if ini == fin else set(range(ini, fin + 1))
            dims = {f: v for f, a, v in datos if a == "DIM"}
            attr_vals = sorted({v for f, a, v in datos if a == attr})
            entra = len(attr_vals) > 0
            prints = r2.errors or r3.errors
            err_txt = ("  ERR " + str(err)) if prints else ""
            print(f"  [{'SI' if entra else 'NO'}] {etiq} fx{ini}-{fin} "
                  f"{attr:<18} -> {attr_vals if attr_vals else '(no guardo)'}"
                  f"   DIM={sorted(dims.values())[:1]}{err_txt}")
        # limpieza: estas secuencias SI existen, borrarlas es seguro
        for seq in creadas:
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {seq}")


if __name__ == "__main__":
    asyncio.run(main())
