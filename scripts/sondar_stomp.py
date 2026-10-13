r"""
Descubre COMO se escribe el stomp en el XML de las secuencias de grandMA2,
UNA CANDIDATA POR SECUENCIA (bisección).

Motivo: el operador reportó que el efecto de cambio de colores queda COLGADO
en los LED. Cuando un cue deja un efecto corriendo (ef7 RGB Rainbow sobre el
COLORRGB) y el cue siguiente escribe un color fijo sobre ese mismo atributo, en
la consola el efecto sigue por encima. Eso se resuelve con STOMP.

La grafía no se puede deducir: la consola no expone el XSD por telnet y el show
es binario. La primera prueba (las 4 candidatas juntas en un cue) hizo que la
consola descartara el cue 2 entero, así que ahora va una por una: cada
candidata en su propia secuencia de scratch, y se mira si el cue 2 conserva los
datos o vuelve vacío.

Control positivo: `attribute_name` y `value_multipart_index` sí se saben que
sobreviven. Si el cue vuelve con datos pero sin la candidata, el nombre está mal
y no que la consola descarte atributos.

Uso: python scripts\sondar_stomp.py
"""
import asyncio
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
SEQ0 = 190
FX = 5
T5 = "\t" * 5

CANDIDATAS = [
    ("A_valor", "atributo stomp en <Value>", "val"),
    ("B_cuedata", "atributo stomp en <CueData>", "cuedata"),
    ("C_elemento", "elemento <Stomp /> dentro del CueData", "elem"),
    ("D_cue", "atributo stomp en <Cue>", "cue"),
    ("E_control", "SIN stomp (control: debe volver con datos)", "nada"),
]


def _cue(num, cand):
    cab = ' value_multipart_index="0" effect_multipart_index="0"'
    if cand == "cuedata":
        cab += ' stomp="true"'
    cue = ' stomp="true"' if cand == "cue" else ""
    L = [f'\t\t<Cue index="{num}"{cue}>',
         f'\t\t\t<Number number="{num}" sub_number="0" />',
         "\t\t\t<CueDatas>", f"{T5}<CueData{cab}>",
         f'{T5}\t<Channel fixture_id="{FX}" attribute_name="COLORRGB1" />']
    if cand == "val":
        L.append(f'{T5}\t<Value stomp="true">100</Value>')
    else:
        L.append(f"{T5}\t<Value>100</Value>")
    if cand == "elem":
        L.append(f"{T5}\t<Stomp />")
    if num == 1:                       # cue 1: encima el efecto que queda colgado
        L += [f'{T5}\t<Effect name="RGB Rainbow 7">',
              f"{T5}\t<No>1</No>", f"{T5}\t<No>7</No>", f"{T5}\t</Effect>"]
    L += [f"{T5}</CueData>", "\t\t\t</CueDatas>",
          '\t\t\t<CuePart index="0">', "\t\t\t\t<CuePartPresetTiming>"]
    L += ["\t\t\t\t\t<PresetTiming />"] * 10
    L += ["\t\t\t\t</CuePartPresetTiming>", "\t\t\t</CuePart>", "\t\t</Cue>"]
    return "\n".join(L)


def secuencia(idx, cand):
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
         ' xmlns="http://schemas.malighting.de/grandma2/xml/MA"'
         ' xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA'
         ' http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd"'
         ' major_vers="3" minor_vers="9" stream_vers="60">',
         '\t<Info datetime="2026-10-02T00:00:00" showfile="sonda stomp" />',
         f'\t<Sequ index="{idx}" name="SONDA STOMP" timecode_slot="255"'
         ' forced_position_mode="0">', '\t\t<Cue xsi:nil="true" />',
         _cue(1, cand), _cue(2, cand), "\t</Sequ>", "</MA>", ""]
    return "\n".join(L)


async def main():
    sello = int(time.time()) % 100000
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")

    async with Ma2() as ma2:
        for i, (nombre, desc, cand) in enumerate(CANDIDATAS):
            seq = SEQ0 + i
            src = EXPORT_DIR / f"ss_{sello}_{i}.xml"
            dst = EXPORT_DIR / f"sso_{sello}_{i}.xml"
            for p in (src, dst):
                p.unlink(missing_ok=True)
            src.write_text(secuencia(seq, cand), encoding="utf-8")

            await ma2.cmd("cd /")
            r = await ma2.cmd(f'Import "{src.name}" At Sequence {seq}')
            if "Overwrite Confirmation" in "\n".join(r.lines):
                await ma2.cmd("1")

            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "sso_{sello}_{i}"')
            for _ in range(25):
                if dst.exists() and dst.stat().st_size > 0:
                    break
                await asyncio.sleep(0.3)
            await ma2.cmd("cd /")
            await ma2.cmd("Clear")

            src.unlink(missing_ok=True)
            if not (dst.exists() and dst.stat().st_size > 0):
                print(f"\n  {nombre:<12} {desc}")
                print("      NO se pudo exportar")
                continue
            txt = dst.read_text(encoding="utf-8", errors="replace")
            dst.unlink(missing_ok=True)

            cue2 = txt.find('<Cue index="2"')
            bloque = txt[cue2:cue2 + 900] if cue2 >= 0 else ""
            con_datos = "COLORRGB1" in bloque
            con_stomp = "stomp" in bloque.lower()
            print(f"\n  {nombre:<12} {desc}")
            print(f"      cue 2 conserva los datos: {'SI' if con_datos else 'NO'}"
                  f"   |  aparece 'stomp': {'SI' if con_stomp else 'NO'}")
            if con_stomp:
                ini = bloque.find("<Cue index=\"2\"")
                for ln in bloque[ini:].splitlines()[:14]:
                    print(f"        {ln.strip()}")

            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {seq}")

    print()
    print("Las secuencias de prueba quedaron borradas.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))