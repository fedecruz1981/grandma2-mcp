r"""
Segunda vuelta: los effects de DIMMER/SHUTTER/posicion necesitan base.

effect_test4.py: `At Effect 7` (RGB Rainbow) guarda sin problema, con o sin
color base. Pero `At Effect 2/3/6/13` sobre fx23-30 dieron cue VACIO cuando se
mandaban SOLOS. Hipotesis: el effect solo queda si el atributo destino ya esta
en el programador (para el arcoiris el destino es COLORRGB, que el fixture
tiene; para Dimmer PWM el destino es DIM, que no estaba cargado).

Se prueba cargando ANTES el atributo destino, y tambien invertido.

Effects del pool relevantes al plan:
  2 Dimmer Chase   -> DIM
  3 Dimmer PWM     -> DIM
  6 Shutter PWM    -> SHUTTER
  7 RGB Rainbow    -> COLORRGB1/2/3        (ya confirmado)
  13/23 Tilt Sin Pan stomp -> PAN/TILT

Uso: python scripts\effect_test5.py
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

CASOS = [
    ("DIM base + Effect 3 (PWM)",
     ["Fixture 23 Thru 30", "At 80", "At Effect 3"]),
    ("DIM base + Effect 2 (Chase)",
     ["Fixture 23 Thru 30", "At 80", "At Effect 2"]),
    ("SHUTTER base + Effect 6",
     ["Fixture 23 Thru 30", 'Attribute "Shutter" At 0', "At Effect 6"]),
    ("DIM + SHUTTER base + Effect 6",
     ["Fixture 23 Thru 30", "At 80", 'Attribute "Shutter" At 0',
      "At Effect 6"]),
    ("PAN base + Effect 13 (stomp) en cabezales",
     ["Fixture 1 Thru 4", "Attribute \"Pan\" At 50",
      "Attribute \"Tilt\" At 50", "At Effect 13"]),
    ("invertido: Effect 3 y despues At 80",
     ["Fixture 23 Thru 30", "At Effect 3", "At 80"]),
    ("DIM base + Effect 3 en stromber fx5-8",
     ["Fixture 5 Thru 8", "At 80", "At Effect 3"]),
]


def resumen(tag):
    ruta = EXPORT_DIR / f"{tag}.xml"
    if not ruta.exists():
        return {}
    root = ET.parse(ruta).getroot()
    agg = {}
    for cd in root.iter(f"{NS}CueData"):
        ch = cd.find(f"{NS}Channel")
        if ch is None:
            continue
        fx = int(ch.get("fixture_id"))
        attr = ch.get("attribute_name")
        val = cd.find(f"{NS}Value")
        eff = cd.find(f"{NS}Effect")
        rate = cd.find(f"{NS}EffectRate")
        info = (fx, val.text if val is not None else None,
                eff.get("name") if eff is not None else None,
                rate.text if rate is not None else None)
        agg.setdefault(attr, []).append(info)
    return agg


async def main():
    creadas = []
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for i, (etiqueta, cmds) in enumerate(CASOS):
            seq = SEQ0 + i
            tag = f"eft5_{i}"
            print("=" * 78)
            print(f"CASO {i}: {etiqueta}")
            await ma2.cmd("cd /")
            await ma2.cmd("Clear")
            for c in cmds:
                r = await ma2.cmd(c)
                if r.errors:
                    print(f"  >>> {c:<38} [ERR {r.errors}]")
            await ma2.cmd(f"Store Cue 1 Sequence {seq} /noconfirm")
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "{tag}"')
            creadas.append(seq)

            agg = resumen(tag)
            if not agg:
                print("  --> VACIO (no guardo nada)")
                continue
            for attr in sorted(agg):
                filas = agg[attr]
                fxs = sorted(f for f, *_ in filas)
                efe = sorted({e for _, _, e, _ in filas if e})
                vals = sorted({v for _, v, _, _ in filas if v is not None})
                rates = sorted({r for *_, r in filas if r})
                print(f"  --> {attr:<16} fx{fxs[0]}-{fxs[-1]} ({len(fxs)})"
                      f"  val={vals or '-'}  effect={efe or '-'}"
                      f"  rate={rates or '-'}")

        print("\n" + "=" * 78)
        print("LIMPIEZA")
        for seq in creadas:
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {seq}")


if __name__ == "__main__":
    asyncio.run(main())
