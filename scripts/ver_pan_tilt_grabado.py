r"""
Verifica que el PAN/TILT de los cabezales quedara escrito en la consola.

Lo que busca, sobre el export real de la secuencia:
  - fx1..fx4 con PAN y TILT = los valores de CABEZAS_PT
  - los cues del baile (Q6 y Q11, cues 1 y 6 de la seq 157) SIN ef17 sobre
    PAN/TILT: si hubiera barrido, el efecto mandaria sobre la posicion y el
    haz no quedaria colgado donde se lo apunta
  - el resto de los cues con ef17 (el barrido manda, la posicion es referencia)

Uso: python scripts\ver_pan_tilt_grabado.py
"""
import asyncio
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402
from ma2_telnet import ANSI  # noqa: E402

EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"

ESPERADO = [(10, 10), (20, 10), (30, 10), (40, 10)]
# De los dos cues de baile de la escena 2, solo uno va con POSICION FIJA:
#   cue 1 (Q6  "Por vos")      -> haces colgados sobre los bailarines
#   cue 6 (Q11 "Lord Bigotin")  -> BARRIDO ef17, que es lo que pidio el operador
#                                 para la coreografia del villano
FIJOS = [1]
CON_BARRIDO = [6]


async def exportar(ma2, seq, sello):
    tag = f"ptv_{seq}_{sello}"
    f = EXPORT / f"{tag}.xml"
    f.unlink(missing_ok=True)
    await ma2.drain()
    await ma2._raw(f"Export Sequence {seq} '{tag}'")
    crudo = await ma2._read_until_prompt(max_wait=6.0)
    if "Overwrite" in ANSI.sub("", crudo or ""):
        await ma2.drain()
        await ma2._raw("2")
        await ma2._read_until_prompt(max_wait=3.0)
    for _ in range(30):
        if f.exists() and f.stat().st_size > 0:
            break
        await asyncio.sleep(0.3)
    if not (f.exists() and f.stat().st_size > 0):
        return None
    root = ET.parse(f).getroot()
    f.unlink(missing_ok=True)
    return root


def leer(root):
    """-> {cue: {"pan":[...], "tilt":[...], "ef_pt": bool, "dim": [...]}}"""
    out = {}
    for cue in root.iter(f"{NS}Cue"):
        idx = cue.get("index")
        if idx is None:
            continue
        pan, tilt, dim = {}, {}, {}
        ef_pt = False
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            e = cd.find(f"{NS}Effect")
            if ch is None:
                continue
            fx = int(ch.get("fixture_id"))
            if not (1 <= fx <= 4):
                continue
            attr = ch.get("attribute_name")
            try:
                v = round(float(va.text), 1) if va is not None else None
            except (TypeError, ValueError):
                v = None
            if attr == "PAN":
                pan[fx] = v
            elif attr == "TILT":
                tilt[fx] = v
            elif attr == "DIM":
                dim[fx] = v
            if attr in ("PAN", "TILT") and e is not None:
                ef_pt = True
        out[int(idx)] = {"pan": pan, "tilt": tilt, "ef_pt": ef_pt, "dim": dim}
    return out


async def main():
    sello = int(time.time()) % 100000
    fallos = []
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")

    async with Ma2() as ma2:
        for seq in (156, 157, 158, 161):
            root = await exportar(ma2, seq, sello)
            if root is None:
                print(f"\n  seq {seq}: no se pudo exportar")
                fallos.append(f"seq {seq}")
                continue
            datos = leer(root)
            print()
            print("=" * 76)
            print(f"SEQ {seq}   PAN/TILT de los 4 cabezales")
            print("=" * 76)
            for idx in sorted(datos):
                d = datos[idx]
                pan = [d["pan"].get(i) for i in (1, 2, 3, 4)]
                tilt = [d["tilt"].get(i) for i in (1, 2, 3, 4)]
                barrido = "barrido ef17" if d["ef_pt"] else "POSICION FIJA"
                ok_pt = all(p is not None and t is not None for p, t in zip(pan, tilt))
                marca = "" if ok_pt else "   <-- FALTA PAN/TILT"
                if not ok_pt:
                    fallos.append(f"seq {seq} cue {idx}: sin PAN/TILT")
                if seq == 157 and idx in FIJOS and d["ef_pt"]:
                    fallos.append(f"seq 157 cue {idx}: deberia ir SIN ef17")
                    marca += "   <-- NO DEBERIA TENER ef17"
                if seq == 157 and idx in CON_BARRIDO and not d["ef_pt"]:
                    fallos.append(f"seq 157 cue {idx} (coreografia): sin ef17")
                    marca += "   <-- FALTA EL ef17 DEL BARRIDO"
                print(f"  cue {idx:>2}: pan={str(pan):<24} tilt={str(tilt):<22} "
                      f"dim={d['dim'].get(1)}  {barrido}{marca}")

        await ma2.drain()
        await ma2._raw("Clear")

    print()
    print("=" * 76)
    print("ESPERADO: pan=[10.0, 20.0, 30.0, 40.0]  tilt=[10.0, 10.0, 10.0, 10.0]")
    print("ESCENA 2: cue 1 (Por vos) = POSICION FIJA | cue 6 (coreografia) = BARRIDO ef17")
    print()
    if fallos:
        print(f"HAY {len(fallos)} PROBLEMAS:")
        for f in fallos[:20]:
            print(f"   - {f}")
    else:
        print("TODO OK: PAN/TILT en todos los cues, cue 1 fijo y cue 6 barriendo.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))