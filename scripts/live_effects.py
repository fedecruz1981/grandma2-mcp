r"""
Como usa el SHOW VIVO los effects, por si hay un patron que a mi me falta.

effect_test5.py: los effects de dimmer/shutter (2 Dimmer Chase, 3 Dimmer PWM,
6 Shutter PWM) no guardan ni con valor base, mientras que 7 RGB Rainbow y
13/23 Tilt Sin Pan stomp si. Puede ser que en este rig esos effects se apliquen
de otra manera, o directamente no se usen.

Se exportan las secuencias vivas con mas chance de tener effects (ARCO IRIS LED
58, BEAN ARCOIRIS 59, shuter 141, DIMER FA 100, DIMER CIRCULO 121, BRUTOS
SHUTER 30, etc.) y se lista (cue, fixture, atributo, effect, rate).

Uso: python scripts\live_effects.py
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

SECUENCIAS = [58, 59, 100, 121, 141, 30, 28, 113, 119, 120, 128, 137, 142]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for seq in SECUENCIAS:
            tag = f"lve{seq}"
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "{tag}"')
            ruta = EXPORT_DIR / f"{tag}.xml"
            if not ruta.exists():
                print(f"--- seq {seq}: no se pudo exportar")
                continue
            root = ET.parse(ruta).getroot()
            nombre = ""
            for s in root.iter(f"{NS}Sequ"):
                nombre = s.get("name") or ""
            hallados = {}
            for cue in root.iter(f"{NS}Cue"):
                ci = cue.get("index")
                if ci is None:
                    continue
                for cd in cue.iter(f"{NS}CueData"):
                    ch = cd.find(f"{NS}Channel")
                    eff = cd.find(f"{NS}Effect")
                    if ch is None or eff is None:
                        continue
                    clave = (eff.get("name"), ch.get("attribute_name"))
                    hallados.setdefault(clave, []).append(
                        (int(ci), int(ch.get("fixture_id"))))
            print("=" * 78)
            print(f"seq {seq}  {nombre!r}")
            if not hallados:
                print("   (sin effects)")
                continue
            for (efe, attr), usos in sorted(hallados.items(),
                                            key=lambda k: str(k[0])):
                cues = sorted({c for c, _ in usos})
                fxs = sorted({f for _, f in usos})
                print(f"   {efe!r:<30} attr={attr:<14} "
                      f"fx{fxs[0]}-{fxs[-1]}  cues={cues[:12]}"
                      f"{'...' if len(cues) > 12 else ''}")


if __name__ == "__main__":
    asyncio.run(main())
