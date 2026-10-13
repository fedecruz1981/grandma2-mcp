r"""
Tercera vuelta: effects 2, 3 y 6 en CADA grupo.

Datos previos:
  - effect 7 (RGB Rainbow) guarda en todos los grupos con RGB (fx5-30). OK.
  - effect 13 (stomp) guarda donde hay PAN/TILT (fx1-4). OK.
  - effects 2/3/6 dieron cue VACIO en fx23-30 incluso con base.
  - el show vivo usa 'Dimmer Sin 1' en fx1-22 y 'Shutter PWM 6' en fx1-4,
    o sea que esos effects SI existen en el rig.

Puede ser que fx23-30 (Protones chico) no soporten effects de dimmer/shutter.
Se prueba grupo por grupo, con el atributo destino cargado antes.

Uso: python scripts\effect_test6.py
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

GRUPOS = [("CM", 1, 4), ("BT", 5, 8), ("FRONT", 9, 14),
          ("BM", 15, 22), ("BF", 23, 30)]
EFECTOS = [2, 3, 6, 1]          # 1 = Dimmer Sin, el que usa el show vivo


def resumen(tag):
    ruta = EXPORT_DIR / f"{tag}.xml"
    if not ruta.exists():
        return {}
    root = ET.parse(ruta).getroot()
    agg = {}
    for cd in root.iter(f"{NS}CueData"):
        ch = cd.find(f"{NS}Channel")
        eff = cd.find(f"{NS}Effect")
        if ch is None:
            continue
        attr = ch.get("attribute_name")
        agg[attr] = eff.get("name") if eff is not None else None
    return agg


async def main():
    casos = []
    for etq, ini, fin in GRUPOS:
        for e in EFECTOS:
            dest = ("DIM" if e in (1, 2, 3) else "SHUTTER")
            base = ("At 80" if dest == "DIM"
                    else 'Attribute "Shutter" At 0')
            casos.append((f"{etq:<6} fx{ini}-{fin:<3} effect {e:<2} ({dest})",
                          [f"Fixture {ini} Thru {fin}", base,
                           f"At Effect {e}"]))

    creadas = []
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for i, (etiqueta, cmds) in enumerate(casos):
            seq = SEQ0 + i
            tag = f"eft6_{i}"
            await ma2.cmd("cd /")
            await ma2.cmd("Clear")
            for c in cmds:
                await ma2.cmd(c)
            await ma2.cmd(f"Store Cue 1 Sequence {seq} /noconfirm")
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "{tag}"')
            creadas.append(seq)
            agg = resumen(tag)
            hay = "GUARDA" if any(v for v in agg.values()) else "  --  "
            det = ", ".join(f"{a}={v}" for a, v in sorted(agg.items()))
            print(f"  [{hay}] {etiqueta:<34} {det[:80]}")

        for seq in creadas:
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {seq}")


if __name__ == "__main__":
    asyncio.run(main())
