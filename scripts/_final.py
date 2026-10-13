import asyncio, sys
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0, "scripts")
from ma2_telnet import Ma2

NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
EXP = Path(r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport")
GRUPOS = [("CM",1,4),("BT",5,8),("FRONT",9,14),("BM",15,22),("BF",23,30)]

async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ma2.cmd("cd /")
        await ma2.cmd('Export Sequence 156 "final156"')
    root = ET.parse(EXP/"final156.xml").getroot()
    datos = {}
    for cue in root.iter(f"{NS}Cue"):
        n = cue.get("index")
        if n is None: continue
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel"); va = cd.find(f"{NS}Value")
            if ch is None: continue
            datos.setdefault(int(n), {}).setdefault(
                int(ch.get("fixture_id")), {})[ch.get("attribute_name")] = (
                va.text if va is not None else "-")
    print(f"SECUENCIA 156  (boton 3.101)  cues en el show: {sorted(datos)}\n")
    for n in sorted(datos):
        print(f"--- Cue {n} ---")
        for g, ini, fin in GRUPOS:
            filas = [fx for fx in range(ini, fin+1) if fx in datos[n]]
            if not filas:
                print(f"   {g:<6} fx{ini}-{fin}: (sin valores)"); continue
            d = datos[n][filas[0]]
            rgb = [d.get("COLORRGB1","-"), d.get("COLORRGB2","-"), d.get("COLORRGB3","-")]
            cm = "COLOR RGB" if rgb[0] != "-" else "sin color"
            print(f"   {g:<6} fx{ini}-{fin}: DIM={d.get('DIM','-'):<4} "
                  f"R/G/B={rgb[0]}/{rgb[1]}/{rgb[2]:<6} "
                  f"SHUTTER={d.get('SHUTTER','-'):<4} {cm}")
        print()
asyncio.run(main())
