r"""
Import: reemplaza o fusiona? y que hace el atributo <Sequ index>?

Pista: los exports muestran `Sequ index = numero_de_secuencia - 1`
(la seq 191 exporta index="190"; la seq 100 exporta index="99"). Si el import
usa el index del XML para decidir el numero, un index corrido crea OTRA
secuencia y deja la destino intacta, que es exactamente lo que paso.

Prueba: marca fx23 DIM=50 en la 191, importa un XML con fx2 DIM=60.
Se prueban las 191 y 192 despues, y se leen los prompts (que traen el nombre).

Uso: python scripts\merge_test.py
"""
import asyncio
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqxml  # noqa: E402
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"


def resumen(tag):
    ruta = EXPORT_DIR / f"{tag}.xml"
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    out = {}
    for cue in root.iter(f"{NS}Cue"):
        if cue.get("index") is None:
            continue
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            if ch is None:
                continue
            out.setdefault(int(cue.get("index")), []).append(
                (int(ch.get("fixture_id")), ch.get("attribute_name"),
                 va.text if va is not None else None))
    return out


async def exportar(ma2, seq, tag):
    await ma2.cmd("cd /")
    await ma2.cmd(f'Export Sequence {seq} "{tag}"')
    for _ in range(10):
        if (EXPORT_DIR / f"{tag}.xml").exists():
            return resumen(tag)
        await asyncio.sleep(0.3)
    return None


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for s in (191, 192):
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {s}")

        # marca en 191
        await ma2.cmd("cd /")
        await ma2.cmd("Clear")
        await ma2.cmd("Fixture 23")
        await ma2.cmd("At 50")
        await ma2.cmd("Store Cue 1 Sequence 191 /noconfirm")

        # XML con fx2 DIM=60, index = 190 (= 191 - 1)
        xml = seqxml.secuencia(190, "MERGE TEST",
                               [(1, [(2, "DIM", 60, None, 0, 1)])])
        (EXPORT_DIR / "merge_in.xml").write_text(xml, encoding="utf-8")

        await ma2.cmd("cd /")
        r = await ma2.cmd('Import "merge_in" At Sequence 191')
        print("  --- respuesta del Import")
        for ln in [x for x in r.body if x.strip()]:
            print(f"    {ln.strip()[:130]}")

        print("\n  --- que hay despues")
        for s in (191, 192):
            await ma2.cmd("cd /")
            p = await ma2.cmd(f"cd Sequence {s}")
            print(f"    cd Sequence {s} -> prompt={p.prompt!r} err={p.errors}")
        d191 = await exportar(ma2, 191, "mo191")
        d192 = await exportar(ma2, 192, "mo192")
        print(f"\n    seq 191 cue1: {d191.get(1) if d191 else None}")
        print(f"    seq 192 cue1: {d192.get(1) if d192 else None}")

        for s in (191, 192):
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {s}")


if __name__ == "__main__":
    asyncio.run(main())
