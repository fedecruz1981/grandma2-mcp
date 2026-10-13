r"""
Captura la forma REAL que la consola guarda para:
  - effect 7 (RGB Rainbow) sobre la rueda COLOR1 de los cabezales
  - effect 17 (P/T Cross) sobre PAN/TILT de los cabezales

Asi el generador usa el form_index/flags correctos en vez de deducirlos.
Uso: python scripts\pt_capture.py
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
    ("effect 7 sobre COLOR1 (rueda), fx1-4",
     ["Fixture 1 Thru 4", 'Attribute "Color1" At 24', "At Effect 7"]),
    ("effect 17 (P/T Cross), fx1-4",
     ["Fixture 1 Thru 4", 'Attribute "Pan" At 50',
      'Attribute "Tilt" At 50', "At Effect 17"]),
    ("effect 7 sobre COLOR1 SIN base, fx1-4",
     ["Fixture 1 Thru 4", "At Effect 7"]),
]


def bloques(ruta):
    root = ET.parse(ruta).getroot()
    out = []
    for cue in root.iter(f"{NS}Cue"):
        if cue.get("index") is None:
            continue
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            ef = cd.find(f"{NS}Effect")
            if ch is None or ef is None:
                continue
            if int(ch.get("fixture_id")) > 4:
                continue
            L = [f'<Channel fixture_id="{ch.get("fixture_id")}"'
                 f' attribute_name="{ch.get("attribute_name")}" />']
            va = cd.find(f"{NS}Value")
            if va is not None:
                L.append(f"<Value>{va.text}</Value>")
            L.append(f'<Effect name="{ef.get("name")}">')
            for no in ef.iter(f"{NS}No"):
                L.append(f"  <No>{no.text}</No>")
            L.append("</Effect>")
            for tag in ("EffectFlags", "EffectRate", "EffectLow",
                        "EffectLowPreset", "EffectHigh", "EffectHighPreset",
                        "EffectPhase", "EffectWidth"):
                e = cd.find(f"{NS}{tag}")
                if e is None:
                    continue
                at = " ".join(f'{k}="{v}"' for k, v in e.attrib.items())
                txt = (e.text or "").strip()
                L.append(f"  <{tag}{(' ' + at) if at else ''}>"
                         f"{txt}</{tag}>")
            out.append("\n".join(L))
    return out


async def main():
    creadas = []
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for i, (etiqueta, cmds) in enumerate(CASOS):
            seq = SEQ0 + i
            tag = f"ptc{i}"
            print("=" * 78)
            print(f"{etiqueta}   (seq {seq})")
            await ma2.cmd("cd /")
            await ma2.cmd("Clear")
            for c in cmds:
                r = await ma2.cmd(c)
                if r.errors:
                    print(f"  >>> {c}  ERR {r.errors}")
            await ma2.cmd(f"Store Cue 1 Sequence {seq} /noconfirm")
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "{tag}"')
            creadas.append(seq)
            bl = bloques(EXPORT_DIR / f"{tag}.xml")
            if not bl:
                print("  (no guardo nada)")
            else:
                for b in bl[:2]:
                    print("  ---")
                    for ln in b.splitlines():
                        print(f"  {ln}")
        for seq in creadas:
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {seq}")


if __name__ == "__main__":
    asyncio.run(main())
