"""
Averigua si el strobo (ef6 sobre SHUTTER) se puede guardar en el grupo BM
(fx15-22, Nebula Max 162) o si la consola lo rechaza.

Metodo: se escribe por linea de comandos (no por XML, que es lo que ya se
probo que falla) en una secuencia scratch, se exporta y se mira que quedo.
Despues se borra la secuencia scratch.

Se prueban 3 vias para el BM:
  A) At Effect 6 Fixture 15.1        (sintaxis normal de efecto en fixture)
  B) At Effect 6 Attribute 18 Fixture 15.1   (forzando el atributo)
  C) At Effect 3 Fixture 15.1        (strobo por dimmer, el plan B)
y de control, la misma via A en un fixture que SI funciona (fx9, FRONT).

Uso: python scripts/test_strobe_bm.py
"""
import asyncio
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")
SCRATCH = 950

PRUEBAS = [
    ("A fx15 At Effect 6 Fixture",            "At Effect 6 Fixture 15.1"),
    ("B fx15 At Effect 6 Attribute 18",       "At Effect 6 Attribute 18 Fixture 15.1"),
    ("C fx15 At Effect 3 Fixture (dimmer)",   "At Effect 3 Fixture 15.1"),
    ("D fx9  At Effect 6 Fixture (control)",  "At Effect 6 Fixture 9.1"),
]


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()}\n")
        # se limpia la secuencia scratch de cualquier prueba anterior
        await ma2.cmd(f"Delete Sequence {SCRATCH}")

        for etiqueta, cmd in PRUEBAS:
            await ma2.cmd("Clear")
            r = await ma2.cmd(cmd)
            for e in r.errors:
                print(f"  {etiqueta}: ERROR {e}")
            await ma2.cmd("cd /")
            r = await ma2.cmd("Store Sequence 1 Cue 1")
            r = await ma2.cmd(f"Store Sequence {SCRATCH} Cue 1")
            for e in r.errors:
                print(f"  {etiqueta}: ERROR store {e}")

            tag = f"stb{SCRATCH}"
            ruta = EXPORT / f"{tag}.xml"
            if ruta.exists():
                ruta.unlink()
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {SCRATCH} "{tag}"')
            for _ in range(15):
                if ruta.exists() and ruta.stat().st_size > 0:
                    break
                await asyncio.sleep(0.3)
            if not (ruta.exists() and ruta.stat().st_size > 0):
                print(f"  {etiqueta}: no se pudo exportar")
                continue
            root = ET.parse(ruta).getroot()
            efectos = []
            for cue in root.iter(f"{NS}Cue"):
                for cd in cue.iter(f"{NS}CueData"):
                    ch = cd.find(f"{NS}Channel")
                    ef = cd.find(f"{NS}Effect")
                    if ef is not None:
                        efectos.append(f"fx{ch.get('fixture_id')} "
                                       f"{ch.get('attribute_name')}={ef.get('name')}")
            print(f"  {etiqueta}: {efectos or 'NO SE GUARDO NADA'}")
            ruta.unlink(missing_ok=True)

        # limpieza
        await ma2.cmd(f"Delete Sequence {SCRATCH}")
        await ma2.cmd("cd /")
        r = await ma2.cmd("SaveShow /noconfirm")
        for ln in [x for x in r.body if x.strip()][:2]:
            print(f"  {ln.strip()[:110]}")


if __name__ == "__main__":
    asyncio.run(main())
