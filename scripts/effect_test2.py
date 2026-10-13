"""
Busca la sintaxis que mete un effect DENTRO de un cue de secuencia.

Contexto: `Assign Effect 3` con fixtures seleccionados en el programador
devuelve "ok" pero NO guarda nada: el XML exportado no tiene ningun tag
<Effect>, solo el atributo effect_multipart_index="0" que siempre es 0.
O sea, es un no-op silencioso. Confirmado leyendo efftest.xml.

El repo solo conoce `Assign Effect {id} Executor {n}`, que es otra cosa
(bindear un effect a un executor), no meterlo en un cue.

Por que importa: el operador eligio grabar multicolor y flash con effect
asignado, y son 28 cues de 53. Si no existe sintaxis, hay que decirlo y
volver al plan de "solo color + nivel, effects a mano".

Se prueban las formas con y sin contexto de cue, cada una en secuencia 170
(tirada), verificando por export si aparece un tag <Effect>.
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
SEQ = 170


def buscar_effect_tags(nombre):
    ruta = EXPORT_DIR / f"{nombre}.xml"
    if not ruta.exists():
        return None, []
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    tags = sorted({m for m in re.findall(r"<(\w*[Ee]ffect\w*)", texto)})
    return texto, tags


async def base_cue(ma2):
    """Deja fx23-30 con color + nivel en el cue 1 de la secuencia 170."""
    await ma2.cmd("cd /")
    await ma2.cmd(f"Delete Sequence {SEQ}")
    await ma2.cmd("Fixture 23 Thru 30")
    await ma2.cmd('Attribute "ColorRGB1" At 100')
    await ma2.cmd('Attribute "ColorRGB2" At 20')
    await ma2.cmd('Attribute "ColorRGB3" At 30')
    await ma2.cmd("At 90")
    await ma2.cmd(f"Store Cue 1 Sequence {SEQ} /noconfirm")


# (etiqueta, comandos previos de contexto, comando de assign)
CASOS = [
    ("desde el cue, con fixtures seleccionados",
     ["cd /", f"cd Sequence {SEQ}", f"cd Sequence {SEQ} Cue 1",
      "Fixture 23 Thru 30"],
     "Assign Effect 3 50"),

    ("desde el cue, sin seleccionar fixtures",
     ["cd /", f"cd Sequence {SEQ}", f"cd Sequence {SEQ} Cue 1"],
     "Assign Effect 3 50"),

    ("con destino explicito Sequence ... Cue",
     ["cd /", "Fixture 23 Thru 30"],
     f"Assign Effect 3 50 Sequence {SEQ} Cue 1"),

    ("con 'To' explicito",
     ["cd /", "Fixture 23 Thru 30"],
     f"Assign Effect 3 50 To Sequence {SEQ} Cue 1"),

    ("objeto Effect explicito",
     ["cd /", "Fixture 23 Thru 30"],
     "Assign Effect Effect 3 50"),

    ("effect sobre el grupo del rig",
     ["cd /", "Group 1"],
     "Assign Effect 3 50"),

    ("assign luego store con /merge",
     ["cd /", "Fixture 23 Thru 30"],
     f"Assign Effect 3 50 | Store Cue 1 Sequence {SEQ} /noconfirm /merge"),
]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        resultados = []

        for etiqueta, previos, assign in CASOS:
            print("=" * 78)
            print(f"CASO: {etiqueta}")
            print(f"  assign: {assign}")
            await base_cue(ma2)
            for c in previos:
                r = await ma2.cmd(c)
                if r.errors:
                    print(f"  previo {c!r} -> ERR {r.errors}")
            for c in assign.split(" | "):
                r = await ma2.cmd(c)
                print(f"  {c:<50} "
                      f"{'ok' if not r.errors else 'ERR ' + str(r.errors)}")
                if r.errors:
                    for ln in [x for x in r.body if x.strip()][:3]:
                        print(f"       {ln.strip()[:130]}")

            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {SEQ} "efchk"')
            texto, tags = buscar_effect_tags("efchk")
            ok = bool(tags)
            print(f"  --> tags de effect en el XML: {tags if tags else 'NINGUNO'}"
                  f"   {'*** FUNCIONA ***' if ok else '(no-op)'}")
            resultados.append((etiqueta, ok))

        print("=" * 78)
        print("RESUMEN")
        for etiqueta, ok in resultados:
            print(f"  {'FUNCIONA' if ok else 'no-op  '}  {etiqueta}")

        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {SEQ}")


if __name__ == "__main__":
    asyncio.run(main())