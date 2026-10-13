"""
El strobo del grupo BM (fx15-22, Nebula Max 162) NO queda guardado al importar:
la consola descarta el <CueData> de SHUTTER con ef6. Todos los otros efectos
del BM si quedan (296 verificados). Hay que averiguar por que y cual es la
forma que si funciona.

Este script arma 4 secuencias scratch, cada una con una variante del ef6 sobre
SHUTTER de los fixtures 15-22, las importa y exporta para ver cual sobrevive:

  V0  tal cual lo genera build_sequences.py  (Value 0 + ef6 sobre SHUTTER)
  V1  solo el efecto, sin el <Value>0</Value> delante
  V2  el efecto sobre DIM en vez de sobre SHUTTER
  V3  Value 100 en vez de 0, con ef6 sobre SHUTTER
  V4  fx9-14 (FRONT) con la variante V0, como control

Despues borra las 4 secuencias scratch y guarda el show.

Uso: python scripts/test_strobe_bm2.py
"""
import asyncio
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seqxml  # noqa: E402
from ma2_telnet import Ma2  # noqa: E402

NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")
BM = list(range(15, 23))
FRONT = list(range(9, 15))

VARIANTES = [
    ("V0_bm_value0_shutter",  BM,    0,   "SHUTTER", 6),
    ("V1_bm_solo_efecto",     BM,    None, "SHUTTER", 6),
    ("V2_bm_efecto_en_dim",   BM,    100, "DIM",     6),
    ("V3_bm_value100_shutter", BM,   100, "SHUTTER", 6),
    ("V4_front_control",      FRONT, 0,   "SHUTTER", 6),
]


def entradas(num, fxs, valor, attr, ef):
    """(fx, attr, valor, (efecto, idx, n_fx)) para una variante de prueba."""
    out = []
    for i, fx in enumerate(fxs):
        if valor is not None:
            out.append((fx, attr, valor, None))
        out.append((fx, attr, None, (ef, 0, len(fxs))))
    return out


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()}\n")
        for nombre, fxs, valor, attr, ef in VARIANTES:
            seq = 950 + [v[0] for v in VARIANTES].index(nombre)
            await ma2.cmd(f"Delete Sequence {seq}")
            xml = seqxml.secuencia(seq - 1, f"SCRATCH {nombre}",
                                   [(1, entradas(1, fxs, valor, attr, ef))])
            archivo = EXPORT / f"{nombre}.xml"
            archivo.write_text(xml, encoding="utf-8")
            await ma2.cmd("cd /")
            r = await ma2.cmd(f'Import "{nombre}" At Sequence {seq}')
            if "Overwrite Confirmation" in "\n".join(r.lines):
                await ma2.cmd("1")

            tag = f"out_{nombre}"
            ruta = EXPORT / f"{tag}.xml"
            ruta.unlink(missing_ok=True)
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "{tag}"')
            for _ in range(15):
                if ruta.exists() and ruta.stat().st_size > 0:
                    break
                await asyncio.sleep(0.3)
            if not (ruta.exists() and ruta.stat().st_size > 0):
                print(f"{nombre:<24} NO SE PUDO EXPORTAR")
                continue
            root = ET.parse(ruta).getroot()
            fx_ef = {}
            for c in root.iter(f"{NS}Cue"):
                for cd in c.iter(f"{NS}CueData"):
                    ch = cd.find(f"{NS}Channel")
                    e = cd.find(f"{NS}Effect")
                    if e is not None:
                        fx_ef.setdefault(ch.get("attribute_name"), set()).add(
                            int(ch.get("fixture_id")))
            resumen = {a: f"{len(v)} fixtures {sorted(v)[:3]}..."
                        for a, v in fx_ef.items()}
            print(f"{nombre:<24} {resumen or 'NO SE GUARDO NADA'}")
            ruta.unlink(missing_ok=True)
            archivo.unlink(missing_ok=True)

        for nombre, *_ in VARIANTES:
            seq = 950 + [v[0] for v in VARIANTES].index(nombre)
            await ma2.cmd(f"Delete Sequence {seq}")
        await ma2.cmd("cd /")
        r = await ma2.cmd("SaveShow /noconfirm")
        for ln in [x for x in r.body if x.strip()][:2]:
            print(f"{ln.strip()[:110]}")


if __name__ == "__main__":
    asyncio.run(main())
