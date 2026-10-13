"""
Que quedo realmente grabado de PAN y TILT en una secuencia.

Por que: el operador pregunta si los cabezales quedan apuntados a algun lado o
si eso queda a cargo suyo. Este script lo responde leyendo el export de la
consola (no el plan), cue por cue, separando dos cosas que se confunden:

  - VALOR de PAN/TILT  = una POSICION guardada (a donde apunta)
  - EFECTO sobre PAN/TILT = un MOVIMIENTO (barrido); no dice a donde apunta

Ejemplo:
    python scripts/ver_pan_tilt.py 158
    python scripts/ver_pan_tilt.py            # las 6 secuencias de la obra

No modifica nada: solo exporta y lee.
"""
import asyncio
import sys
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402

NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")
OBRA = {156: "E1 POR VOS", 157: "E2 SOY LORD BIGOTIN",
        158: "E3 LA MIRADA DORADA", 159: "E4 REINA GITANA",
        160: "E5 TODO EN GRIS ES MÁS DIVERTIDO", 161: "E6 SI SOLAMENTE LO QUERÉS"}


def leer(ruta):
    """{cue: {'PAN': {fx: valor}, 'TILT': {...}}, efectos: {cue: {attr: {nombre}}}}"""
    root = ET.parse(ruta).getroot()
    pos, ef = defaultdict(lambda: defaultdict(dict)), defaultdict(lambda: defaultdict(set))
    for cue in root.iter(f"{NS}Cue"):
        if cue.get("index") is None:
            continue
        ci = cue.get("index")
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            e = cd.find(f"{NS}Effect")
            at = ch.get("attribute_name")
            if at not in ("PAN", "TILT"):
                continue
            fx = int(ch.get("fixture_id"))
            if va is not None:
                pos[ci][at][fx] = round(float(va.text), 1)
            if e is not None:
                ef[ci][at].add(e.get("name"))
    return pos, ef


async def main():
    secs = [int(a) for a in sys.argv[1:]] or sorted(OBRA)
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for seq in secs:
            tag = f"pt_{seq}"
            ruta = EXPORT / f"{tag}.xml"
            ruta.unlink(missing_ok=True)
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "{tag}"')
            for _ in range(15):
                if ruta.exists() and ruta.stat().st_size:
                    break
                await asyncio.sleep(0.3)
            print("=" * 74)
            print(f"sec {seq}  {OBRA.get(seq, '')}")
            print("=" * 74)
            if not (ruta.exists() and ruta.stat().st_size):
                print("  no se pudo exportar\n")
                continue
            pos, ef = leer(ruta)
            ruta.unlink(missing_ok=True)
            # un cue puede tener SOLO efecto (sin valor): hay que mirar la union
            cues = sorted(set(pos) | set(ef), key=int)
            print("  cue  | PAN: posicion guardada      | efecto sobre PAN/TILT")
            print("  -----+---------------------------+---------------------------")
            for ci in cues:
                p = pos[ci].get("PAN", {})
                t = pos[ci].get("TILT", {})
                e = sorted(ef[ci].get("PAN", set()) | ef[ci].get("TILT", set()))
                pv = ("fx" + ",".join(str(k) for k in sorted(p))) if p else "NINGUNA"
                tv = ("fx" + ",".join(str(k) for k in sorted(t))) if t else ""
                print(f"  {ci:>4} | {pv:<25} | {', '.join(e) if e else 'ninguno'}"
                      + (f"   (TILT: {tv})" if tv else ""))
            print()


if __name__ == "__main__":
    asyncio.run(main())
