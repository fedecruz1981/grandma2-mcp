import asyncio, sys
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0, "scripts")
from ma2_telnet import Ma2

NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
EXP = Path(r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport")

def cues(tag):
    p = EXP / f"{tag}.xml"
    if not p.exists(): return None
    root = ET.parse(p).getroot()
    out = {}
    for cue in root.iter(f"{NS}Cue"):
        n = cue.get("index")
        if n is None: continue
        out[int(n)] = sum(1 for _ in cue.iter(f"{NS}CueData"))
    return out

async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        # 1) estado actual
        await ma2.cmd("cd /")
        await ma2.cmd('Export Sequence 156 "chk1"')
        print(f"ANTES  : {cues('chk1')}")

        # 2) reponer el cue 2 (hold) - solo toca el cue 2
        await ma2.cmd("cd /")
        await ma2.cmd("Clear")
        r = await ma2.cmd("Store Cue 2 Sequence 156 /noconfirm")
        print(f"store cue 2: {'ok' if not r.errors else r.errors}")

        # 3) verificar
        await ma2.cmd("cd /")
        await ma2.cmd('Export Sequence 156 "chk2"')
        d = cues("chk2")
        print(f"DESPUES: {d}")
        print(f"cues 1-5 completos: {sorted(d) == [1,2,3,4,5]}")

        # 4) el boton sigue apuntando a la secuencia?
        await ma2.cmd("cd /")
        r = await ma2.cmd("cd Executor 3.101")
        print(f"\nprompt boton 3.101: {r.prompt!r}")

        # 5) guardar
        await ma2.cmd("cd /")
        r = await ma2.cmd("SaveShow /noconfirm")
        for ln in [x for x in r.body if x.strip()][:2]:
            print(f"  {ln.strip()}")
asyncio.run(main())
