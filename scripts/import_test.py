r"""
Prueba si la consola IMPORTA un XML exportado.

Por que: `At Effect N` guarda effects, pero con limites por tipo de fixture
(fx23-30 no aceptan effects de dimmer/shutter). Si `Import` funciona, se puede
generar el XML completo de una secuencia -- cues, colores, niveles, shutter y
TODOS los effects -- y meterlo de una sola vez, sin depender de las rarezas del
procesamiento de comandos.

Prueba conservadora:
  1. se toma un export real del show vivo (lve100 = seq DIMER FA, con effect
     Dimmer Sin 1 en fx1-22)
  2. se le cambia el indice a 191 y el nombre a "IMP TEST"
  3. se guarda en importexport\imp_in.xml
  4. `Import Sequence 191 "imp_in"`
  5. `Export Sequence 191 "imp_out"`  y se compara cue por cue
  6. se borra la 191

Si el round-trip sale identico, la via de importar sirve.
Uso: python scripts\import_test.py
"""
import asyncio
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
ORIGEN = EXPORT_DIR / "lve100.xml"
SEQ = 191


def resumen(ruta):
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    out = {}
    for cue in root.iter(f"{NS}Cue"):
        ci = cue.get("index")
        if ci is None:
            continue
        filas = []
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            eff = cd.find(f"{NS}Effect")
            if ch is None:
                continue
            filas.append((
                int(ch.get("fixture_id")),
                ch.get("attribute_name"),
                va.text if va is not None else None,
                eff.get("name") if eff is not None else None))
        out[int(ci)] = sorted(filas)
    return out


async def main():
    if not ORIGEN.exists():
        print(f"falta {ORIGEN.name}; correr live_effects.py antes")
        return

    texto = ORIGEN.read_text(encoding="utf-8")
    texto = re.sub(r'<Sequ index="\d+"', f'<Sequ index="{SEQ - 1}"', texto, count=1)
    texto = re.sub(r'name="[^"]*"', 'name="IMP TEST"', texto, count=1)
    destino = EXPORT_DIR / "imp_in.xml"
    destino.write_text(texto, encoding="utf-8")
    print(f"escrito {destino}  ({len(texto)} bytes)")

    async with Ma2() as ma2:
        await ma2.at_prompt()
        esperado = resumen(ORIGEN)

        for forma in (f'Import Sequence {SEQ} "imp_in"',
                      f'Import "imp_in" At Sequence {SEQ}'):
            await ma2.cmd("cd /")
            r = await ma2.cmd(forma)
            print(f">>> {forma}")
            print(f"    [{'ok' if not r.errors else 'ERR ' + str(r.errors)}]")
            for ln in [x for x in r.body if x.strip()][:4]:
                print(f"      {ln.strip()[:140]}")

            await ma2.cmd("cd /")
            r = await ma2.cmd(f"cd Sequence {SEQ}")
            existe = not r.errors
            print(f"    secuencia {SEQ} existe: {existe}  ({r.prompt!r})")
            if existe:
                break

        if existe:
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {SEQ} "imp_out"')
            obtenido = resumen(EXPORT_DIR / "imp_out.xml")
            if obtenido is None:
                print("  no se genero imp_out.xml")
            else:
                print(f"\n  cues importados: {sorted(obtenido)}")
                print(f"  cues esperados : {sorted(esperado)}")
                igual = obtenido == esperado
                print(f"  ROUND-TRIP IDENTICO: {igual}")
                if not igual:
                    for c in sorted(set(obtenido) | set(esperado)):
                        a, b = esperado.get(c), obtenido.get(c)
                        if a != b:
                            print(f"    cue {c}: orig {len(a) if a else 0} "
                                  f"filas / imp {len(b) if b else 0} filas")
                            if a and b:
                                for x, y in zip(a, b):
                                    if x != y:
                                        print(f"       orig {x}")
                                        print(f"       imp  {y}")
                                        break
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {SEQ}")
            print(f"\n  (secuencia {SEQ} borrada)")

        await ma2.cmd("cd /")
        r = await ma2.cmd("SaveShow /noconfirm")
        for ln in [x for x in r.body if x.strip()][:2]:
            print(f"  {ln.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
