r"""
Import sobre una secuencia EXISTENTE: como evitar el dialogo de Overwrite.

Se probo que Import sobre una secuencia que ya existe abre:
    Overwrite Confirmation : ... object "Sequ 191" :
    [1]: Overwrite  2: Overwrite|All  3: Insert  4: Insert|All  5: Cancel
y si no se contesta, el comando siguiente se come como respuesta del dialogo.

Se prueban dos caminos:
  A) `Import "file" At Sequence 191 /overwrite`  (por si el flag existe)
  B) Import normal + contestar "1" (Overwrite) cuando aparece el dialogo

Ademas se confirma que <Sequ index> = numero_de_secuencia - 1.

Uso: python scripts\import_overwrite_test.py
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
SEQ = 191


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


async def importar(ma2, nombre, target, flag=""):
    """Manda el Import y, si sale el dialogo, contesta Overwrite (1)."""
    await ma2.cmd("cd /")
    cmd = f'Import "{nombre}" At Sequence {target}{flag}'
    r = await ma2.cmd(cmd)
    texto = "\n".join(r.lines)
    if "Overwrite Confirmation" in texto:
        print("      -> salio el dialogo de Overwrite; contesto 1")
        r2 = await ma2.cmd("1")
        texto += "\n" + "\n".join(r2.lines)
    return texto


async def marcar(ma2):
    await ma2.cmd("cd /")
    await ma2.cmd(f"Delete Sequence {SEQ}")
    await ma2.cmd("cd /")
    await ma2.cmd("Clear")
    await ma2.cmd("Fixture 23")
    await ma2.cmd("At 50")
    await ma2.cmd("Store Cue 1 Sequence %d /noconfirm" % SEQ)


async def main():
    # XML con fx2 DIM=60, index = SEQ-1 = 190
    xml = seqxml.secuencia(SEQ - 1, "OVR TEST",
                           [(1, [(2, "DIM", 60, None, 0, 1)])])
    (EXPORT_DIR / "ovr_in.xml").write_text(xml, encoding="utf-8")

    async with Ma2() as ma2:
        await ma2.at_prompt()

        print("== A) con flag /overwrite")
        await marcar(ma2)
        texto = await importar(ma2, "ovr_in", SEQ, " /overwrite")
        for ln in [x for x in texto.splitlines() if x.strip()]:
            print(f"      {ln.strip()[:120]}")
        d = await exportar(ma2, SEQ, "ovr_a")
        print(f"      cue1 = {d.get(1) if d else None}")

        print("\n== B) sin flag + contestar 1")
        await marcar(ma2)
        texto = await importar(ma2, "ovr_in", SEQ)
        for ln in [x for x in texto.splitlines() if x.strip()]:
            print(f"      {ln.strip()[:120]}")
        d = await exportar(ma2, SEQ, "ovr_b")
        print(f"      cue1 = {d.get(1) if d else None}")

        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {SEQ}")


if __name__ == "__main__":
    asyncio.run(main())
