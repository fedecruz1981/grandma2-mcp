r"""
Detalle del comando que SI funciona: `At Effect N`.

`At Effect N` aplica el effect del pool N a la seleccion actual y al grabar
queda guardado como <Effect> dentro del CueData (confirmado en
effect_test3.py caso 6, y coincide con el formato de seq_0059.xml).

Falta saber, para cada effect del pool:
  - a que ATRIBUTO lo aplica (DIM? COLORRGB? SHUTTER?)
  - si convive con un color/nivel estatico ya cargado en el programador
  - con que rate / low / high / phase queda

Eso define como hay que escribir los 28 cues con effect del plan:
  2 Dimmer Chase      -> DIM
  3 Dimmer PWM        -> DIM
  6 Shutter PWM       -> SHUTTER
  7 RGB Rainbow       -> COLORRGB1/2/3

Metodo: una secuencia por caso, export y resumen por atributo.
Uso: python scripts\effect_test4.py
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
    # (etiqueta, comandos antes del Store)
    ("Effect 3 (Dimmer PWM) - atributo?",
     ["Fixture 23 Thru 30", "At Effect 3"]),
    ("Effect 6 (Shutter PWM) - atributo?",
     ["Fixture 23 Thru 30", "At Effect 6"]),
    ("Effect 2 (Dimmer Chase) - atributo?",
     ["Fixture 23 Thru 30", "At Effect 2"]),
    ("color + nivel + Effect 7 juntos",
     ["Fixture 23 Thru 30", 'Attribute "ColorRGB1" At 100',
      'Attribute "ColorRGB2" At 20', 'Attribute "ColorRGB3" At 30',
      "At 70", "At Effect 7"]),
    ("BF estatico + BM con Effect 7 (grupos mezclados)",
     ["Fixture 23 Thru 30", 'Attribute "ColorRGB1" At 100',
      "At 80",
      "Fixture 15 Thru 22", 'Attribute "ColorRGB1" At 0',
      'Attribute "ColorRGB2" At 40', 'Attribute "ColorRGB3" At 100',
      "At 60", "At Effect 7"]),
    ("Effect 13 (Tilt Sin Pan stomp)",
     ["Fixture 23 Thru 30", "At Effect 13"]),
    ("orden invertido: Effect 7 y despues el nivel",
     ["Fixture 23 Thru 30", "At Effect 7", "At 80"]),
]


def resumen(tag):
    ruta = EXPORT_DIR / f"{tag}.xml"
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    por_attr = {}
    for cd in root.iter(f"{NS}CueData"):
        ch = cd.find(f"{NS}Channel")
        if ch is None:
            continue
        fx = int(ch.get("fixture_id"))
        attr = ch.get("attribute_name")
        val = cd.find(f"{NS}Value")
        eff = cd.find(f"{NS}Effect")
        rate = cd.find(f"{NS}EffectRate")
        lo = cd.find(f"{NS}EffectLow")
        hi = cd.find(f"{NS}EffectHigh")
        claves = sorted({f for f, a in por_attr if a == attr})
        if not claves:
            claves = [fx]
        por_attr.setdefault((fx, attr), ())
        e = por_attr[(fx, attr)]
        info = {"val": val.text if val is not None else None,
                "eff": eff.get("name") if eff is not None else None,
                "rate": rate.text if rate is not None else None,
                "low": lo.text if lo is not None else None,
                "high": hi.text if hi is not None else None}
        # guarda el primero de cada atributo
        if e == ():
            por_attr[(fx, attr)] = info
    # agrupa por atributo
    agg = {}
    for (fx, attr), info in por_attr.items():
        agg.setdefault(attr, []).append((fx, info))
    return agg


async def main():
    creadas = []
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for i, (etiqueta, cmds) in enumerate(CASOS):
            seq = SEQ0 + i
            tag = f"eft4_{i}"
            print("=" * 78)
            print(f"CASO {i}: {etiqueta}")
            await ma2.cmd("cd /")
            await ma2.cmd("Clear")
            for c in cmds:
                r = await ma2.cmd(c)
                est = "ok" if not r.errors else "ERR " + str(r.errors)
                print(f"  >>> {c:<40} [{est}]")
                for ln in [x for x in r.body if x.strip()][:2]:
                    print(f"        {ln.strip()[:110]}")
            r = await ma2.cmd(f"Store Cue 1 Sequence {seq} /noconfirm")
            print(f"  >>> Store Cue 1 Sequence {seq} /noconfirm "
                  f"[{'ok' if not r.errors else 'ERR'}]")
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "{tag}"')
            creadas.append(seq)

            agg = resumen(tag)
            if not agg:
                print("  --> VACIO")
                continue
            for attr in sorted(agg):
                filas = agg[attr]
                fxs = sorted(f for f, _ in filas)
                infos = [inf for _, inf in filas]
                efe = {inf["eff"] for inf in infos if inf["eff"]}
                vals = {inf["val"] for inf in infos}
                rate = {inf["rate"] for inf in infos}
                lo = {inf["low"] for inf in infos}
                hi = {inf["high"] for inf in infos}
                print(f"  --> {attr:<16} fx{fxs[0]}-{fxs[-1]} ({len(fxs)})"
                      f"  val={sorted(v for v in vals if v is not None) or '-'}"
                      f"  effect={sorted(efe) if efe else '-'}"
                      f"  rate={sorted(r for r in rate if r) or '-'}"
                      f"  low/high={sorted(l for l in lo if l) or '-'}"
                      f"/{sorted(h for h in hi if h) or '-'}")

        print("\n" + "=" * 78)
        print("LIMPIEZA")
        for seq in creadas:
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {seq}")


if __name__ == "__main__":
    asyncio.run(main())
