r"""
Valores reales que el show vivo usa en los cabezales (fx1-4).

Por que: fx1-4 no tienen RGB, solo rueda de color COLOR1 (ver cm_probe.py).
En vez de inventar posiciones de rueda, se leen de los cues que ya existen en
el show para saber que COLOR1 usa el operador para "White 4.11", "blue 4.3",
etc. Tambien se ven Gobo/Focus/Prism y el Shutter.

Se exportan las secuencias vivas que tocan fx1-4 y se listan, por cue, los
atributos de fx1-4 con su valor y el nombre del preset referenciado.
Uso: python scripts\cm_palette.py
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

SECUENCIAS = [137, 142, 45, 46, 47, 59, 58, 141, 100, 121, 30, 60]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for seq in SECUENCIAS:
            tag = f"cmpal{seq}"
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "{tag}"')
            ruta = EXPORT_DIR / f"{tag}.xml"
            if not ruta.exists():
                continue
            root = ET.parse(ruta).getroot()
            nombre = ""
            for s in root.iter(f"{NS}Sequ"):
                nombre = s.get("name") or ""
            lineas = []
            for cue in root.iter(f"{NS}Cue"):
                ci = cue.get("index")
                if ci is None:
                    continue
                for cd in cue.iter(f"{NS}CueData"):
                    ch = cd.find(f"{NS}Channel")
                    if ch is None:
                        continue
                    fx = int(ch.get("fixture_id"))
                    if fx > 4:
                        continue
                    va = cd.find(f"{NS}Value")
                    pr = cd.find(f"{NS}Preset")
                    val = va.text if va is not None else "-"
                    pn = pr.get("name") if pr is not None else ""
                    lineas.append((int(ci), fx, ch.get("attribute_name"),
                                   val, pn))
            if not lineas:
                continue
            print("=" * 92)
            print(f"seq {seq}  {nombre!r}")
            # agrupa por cue y atributo
            agg = {}
            for ci, fx, attr, val, pn in lineas:
                agg.setdefault((ci, attr), {"vals": set(), "presets": set(),
                                            "fxs": set()})
                agg[(ci, attr)]["vals"].add(val)
                agg[(ci, attr)]["fxs"].add(fx)
                if pn:
                    agg[(ci, attr)]["presets"].add(pn)
            for (ci, attr), d in sorted(agg.items()):
                fxs = sorted(d["fxs"])
                vals = sorted(d["vals"])
                pre = sorted(d["presets"])
                print(f"   cue{ci:<3} {attr:<16} fx{fxs[0]}-{fxs[-1]}  "
                      f"val={vals[:6]}  preset={pre[:3]}")


if __name__ == "__main__":
    asyncio.run(main())
