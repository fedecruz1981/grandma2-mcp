"""
Exporta TODAS las secuencias del show a XML y las parsea a JSON.

Por que Export y no List: `List Preset` devuelve el pool de presets, no el
contenido del cue (devuelve lo mismo para 155 secuencias distintas).
`Export` es el comando documentado que vuelca el contenido real a MA XML:

    [Channel]> Export Sequence 137 "cuelvo137"

Escribe en gma2_V_3.9.60/importexport/<nombre>.xml con los <CueData>
valores exactos por fixture y atributo. Ahi esta el blanco de "malvado".

Export NO modifica el show: solo escribe un archivo.

Uso: python scripts/sweep_sequences.py [max_seq]
"""
import asyncio
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dotenv import load_dotenv

load_dotenv(HERE.parent / ".env")

from ma2_telnet import Ma2

IE_DIR = Path(
    r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport"
)
OUT = HERE.parent / "data" / "cues.json"
NS = {"m": "http://schemas.malighting.de/grandma2/xml/MA"}


def parse_xml(path: Path) -> dict | None:
    """Convierte un export de Sequence a un dict legible."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None

    ns = NS["m"]
    seq = root.find(f"{{{ns}}}Sequ")
    if seq is None:
        return None

    # <Sequ index="136" name="malvado">  -> index es base 0
    try:
        number = int(seq.get("index", "-1")) + 1
    except ValueError:
        number = -1

    appearance = seq.find(f"{{{ns}}}Appearance")
    seq_color = appearance.get("Color") if appearance is not None else None

    cues = []
    for cue in seq.findall(f"{{{ns}}}Cue"):
        idx_el = cue.find(f"{{{ns}}}Number")
        if idx_el is None:
            continue  # <Cue xsi:nil="true"/> = cue vacio
        cue_no = int(idx_el.get("number", "0"))

        # tiempos de fade/delay por preset type (9 tipos)
        timings = {}
        part = cue.find(f"{{{ns}}}CuePart")
        if part is not None:
            pt = part.find(f"{{{ns}}}CuePartPresetTiming")
            if pt is not None:
                for n, t in enumerate(pt.findall(f"{{{ns}}}PresetTiming"), start=1):
                    if t.attrib:
                        timings[n] = dict(t.attrib)

        # valores por fixture
        fixtures: dict[int, dict[str, dict]] = {}
        for cd in cue.iter(f"{{{ns}}}CueData"):
            ch = cd.find(f"{{{ns}}}Channel")
            if ch is None:
                continue
            fid = int(ch.get("fixture_id", "0"))
            attr = ch.get("attribute_name", "?")
            val_el = cd.find(f"{{{ns}}}Value")
            value = val_el.text if val_el is not None else None

            entry = {"value": value}
            pre = cd.find(f"{{{ns}}}Preset")
            if pre is not None:
                entry["preset"] = pre.get("name")
                entry["preset_no"] = ".".join(
                    n.text for n in pre.findall(f"{{{ns}}}No") if n.text
                )
            fx = fixtures.setdefault(fid, {})
            if attr in fx:  # multipartes (efectos): suffijo
                n = 2
                while f"{attr}.{n}" in fx:
                    n += 1
                attr = f"{attr}.{n}"
            fx[attr] = entry

        if fixtures or timings:
            cues.append({"cue": cue_no, "timings": timings, "fixtures": fixtures})

    return {
        "sequence": number,
        "name": seq.get("name", ""),
        "appearance": seq_color,
        "cues": cues,
    }


async def main():
    max_seq = int(sys.argv[1]) if len(sys.argv) > 1 else 200

    IE_DIR.mkdir(parents=True, exist_ok=True)
    # limpia exports previos mios
    for old in IE_DIR.glob("seq_*.xml"):
        old.unlink()

    print(f"exportando secuencias 1..{max_seq} ...\n")
    async with Ma2() as ma2:
        done = 0
        for n in range(1, max_seq + 1):
            name = f"seq_{n:04d}"
            r = await ma2.cmd(f'export sequence {n} "{name}"')
            bad = "Error" in r.raw or "WARNING" in r.raw
            exists = (IE_DIR / f"{name}.xml").exists()
            done += 1 if exists else 0
            if n % 25 == 0 or (not exists and n > 155):
                print(f"  {n:>4} ... {done} exportados")
            if bad and n <= 3:
                print(f"  aviso en {n}: {r.lines}")
            # si dejo de exportar antes de 155, terminamos
            if not exists and n > 160:
                print(f"  se corta en {n}: la secuencia no existe")
                break

    print(f"\nleyendo {len(list(IE_DIR.glob('seq_*.xml')))} archivos xml\n")
    out = {}
    for f in sorted(IE_DIR.glob("seq_*.xml")):
        d = parse_xml(f)
        if d and d["sequence"] > 0:
            out[d["sequence"]] = d

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    con_cues = [d for d in out.values() if d["cues"]]
    print(f"secuencias con contenido: {len(con_cues)} / {len(out)}")
    print(f"cues totales: {sum(len(d['cues']) for d in out.values())}")
    print(f"escrito en {OUT}")


if __name__ == "__main__":
    asyncio.run(main())