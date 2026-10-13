r"""
Rueda de color de los cabezales, sacada de los presets de color del show.

El XML de un preset guarda los valores POR TIPO DE FIXTURE:

  <PresetValue Value="5.5">
    <ChannelType fixture_type="BEAMER 250 MINI CCT 15 channel"
                 module="1" attribute="COLOR1" />
  </PresetValue>

O sea que cada preset de color ya trae la posicion de rueda de los cabezales
(fx1-4) y el RGB de cada barra. Eso da el mapa completo nombre -> COLOR1 sin
inventar nada, y ademas el RGB que el operador usa para cada color.

Uso: python scripts\wheel_map.py
"""
import asyncio
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
DATA = Path(__file__).resolve().parent.parent / "data"
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
DESDE, HASTA = 1, 45

# tipos de fixture tal como los nombra el XML, en el orden de las barras
TIPOS = [
    ("CM", "BEAMER 250 MINI"),
    ("BT", "STROMBER"),
    ("FRONT", "NEBULA FLAT 210"),
    ("BM", "NEBULA MAX 162"),
    ("BF", "PROTONE LED FRENTE"),
]


def leer(tag):
    ruta = EXPORT_DIR / f"{tag}.xml"
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    nombre = ""
    for p in root.iter(f"{NS}Preset"):
        nombre = (p.get("name") or "").strip()
    por_tipo = {}
    for pv in root.iter(f"{NS}PresetValue"):
        val = pv.get("Value")
        for ct in pv.iter(f"{NS}ChannelType"):
            ft = (ct.get("fixture_type") or "").upper()
            attr = ct.get("attribute")
            for etq, pat in TIPOS:
                if pat in ft:
                    por_tipo.setdefault(etq, {})[attr] = val
    return nombre, por_tipo


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        filas = {}
        for n in range(DESDE, HASTA + 1):
            tag = f"cp_{n}"
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Preset 4.{n} "{tag}"')
            d = leer(tag)
            if d is None:
                continue
            nombre, por_tipo = d
            if not nombre:
                continue
            filas[n] = {"nombre": nombre, "tipos": por_tipo}
            cm = por_tipo.get("CM", {})
            bf = por_tipo.get("BF", {})
            bm = por_tipo.get("BM", {})
            bt = por_tipo.get("BT", {})
            fr = por_tipo.get("FRONT", {})

            def rgb(d):
                if "COLORRGB1" not in d:
                    return "-"
                return (f"{d.get('COLORRGB1','?')}/{d.get('COLORRGB2','?')}"
                        f"/{d.get('COLORRGB3','?')}")

            print(f"  4.{n:<2} {nombre:<18} "
                  f"CM COLOR1={cm.get('COLOR1','-'):<6} "
                  f"BF {rgb(bf):<16} BM {rgb(bm):<16} BT {rgb(bt):<16} "
                  f"FRONT {rgb(fr)}")

        (DATA / "wheel_map.json").write_text(
            json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n  {len(filas)} presets -> data/wheel_map.json")


if __name__ == "__main__":
    asyncio.run(main())
