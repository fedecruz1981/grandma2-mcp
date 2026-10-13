"""
Verifica la sintaxis de `Assign Effect` y si SHUTTER se puede guardar.

Por que: el operador eligio grabar los multicolor y los flash con effect
asignado, y elegir SHUTTER abierto/cerrado en CM. Son 28 cues con effect y 15
multicolor, asi que la sintaxis tiene que estar confirmada antes de tocar el
show, no improvisada.

Metodo: se trabaja sobre la secuencia 170 (tirada), que se borra al final.
Cada prueba escribe valores distinguibles y se verifica con Export + XML, que
es el unico read-back fiable (el Programmer no lista la seleccion).

Pool de effects (data/_effects.txt):
   2 Dimmer Chase (1 param)   3 Dimmer PWM (1)    6 Shutter PWM (1)
   7 RGB Rainbow (3)          8 =RGB Rainbow (3)  <- copia del 7
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
TEST_SEQ = 170


def volcar_xml(nombre):
    ruta = EXPORT_DIR / f"{nombre}.xml"
    if not ruta.exists():
        return None, []
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    root = ET.fromstring(texto)
    filas = []
    for cue in root.iter(f"{NS}Cue"):
        idx = cue.get("index")
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            if ch is None:
                continue
            filas.append(f"cue{idx} fx{ch.get('fixture_id')} "
                         f"{ch.get('attribute_name')}="
                         f"{va.text if va is not None else '-'}")
    return texto, filas


async def probar(ma2, etiqueta, cmds):
    print("=" * 78)
    print(f"PRUEBA: {etiqueta}")
    for c in cmds:
        r = await ma2.cmd(c)
        estado = "ok" if not r.errors else f"ERR {r.errors}"
        print(f"  {c:<46} {estado}")


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()

        # --- A: SHUTTER se puede escribir y guardar?
        print("#" * 78)
        print("# A) SHUTTER: se guarda? (el operador lo quiere en CM)")
        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {TEST_SEQ}")
        await probar(ma2, "shutter abierto en fx1-4", [
            "Fixture 1 Thru 4",
            'Attribute "Shutter" At 100',
            'Attribute "ColorRGB1" At 100',
            'Attribute "ColorRGB2" At 90',
            'Attribute "ColorRGB3" At 77',
            "At 80",
            f"Store Cue 1 Sequence {TEST_SEQ} /noconfirm",
        ])
        await ma2.cmd("cd /")
        await ma2.cmd(f'Export Sequence {TEST_SEQ} "shut"')
        texto, filas = volcar_xml("shut")
        print("  --- valores guardados ---")
        for f in filas[:14]:
            print(f"     {f}")
        print(f"  SHUTTER guardado: "
              f"{'SI' if any('SHUTTER' in f for f in filas) else 'NO'}")
        print("  --- XML crudo (primeras lineas del cue) ---")
        if texto:
            ini = texto.find("<Cue")
            for ln in texto[ini:ini + 1400].splitlines():
                if ln.strip():
                    print(f"     {ln.strip()[:150]}")

        # --- B: sintaxis de Assign Effect
        print()
        print("#" * 78)
        print("# B) Assign Effect: que forma acepta y como aparece en el XML")
        VARIANTES = [
            ("effect 3 sin parametros", "Assign Effect 3"),
            ("effect 3 con 1 param", "Assign Effect 3 50"),
            ("effect 3 con velocidad Fast", "Assign Effect 3 Fast"),
            ("effect 3 con 2 params", "Assign Effect 3 50 1"),
            ("effect 7 con 3 params", "Assign Effect 7 50 50 50"),
            ("effect 7 con 2 params", "Assign Effect 7 50 50"),
        ]
        for etiqueta, cmd in VARIANTES:
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {TEST_SEQ}")
            await ma2.cmd("Fixture 23 Thru 30")
            await ma2.cmd('Attribute "ColorRGB1" At 100')
            await ma2.cmd('Attribute "ColorRGB2" At 20')
            await ma2.cmd('Attribute "ColorRGB3" At 30')
            await ma2.cmd("At 90")
            r = await ma2.cmd(cmd)
            estado = "ok" if not r.errors else f"ERR {r.errors}"
            print(f"\n  >>> {cmd:<28} {estado}")
            if r.errors:
                for ln in [x for x in r.body if x.strip()][:4]:
                    print(f"       {ln.strip()[:140]}")
                continue
            await ma2.cmd(f"Store Cue 1 Sequence {TEST_SEQ} /noconfirm")
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {TEST_SEQ} "efftest"')
            texto, filas = volcar_xml("efftest")
            if texto is None:
                print("       no se genero XML")
                continue
            coneff = [f for f in filas if "ffect" in f]
            print(f"       filas totales={len(filas)}  con effect={len(coneff)}")
            for f in (coneff or filas[:4])[:6]:
                print(f"         {f}")

        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {TEST_SEQ}")
        print(f"\nsecuencia {TEST_SEQ} de prueba borrada")


if __name__ == "__main__":
    asyncio.run(main())