"""
¿Se puede crear un cue VACIO, para que la numeracion siga al cue sheet?

Por que: en la Escena 1, Q2 tiene las cuatro celdas con guion largo
('—' = no cambiar). Es un hold legitimo del LD, pero no genera ningun valor,
y si se lo salta la secuencia queda con cues 1 y 3 y un hueco en el 2. Eso
desalinea el conteo contra el PDF, que es justo lo que el operador va a usar
en el，一场.

Se prueban tres caminos sobre la secuencia 170 (tirada):
  A) Store del cue sin nada seleccionado, precedido de Clear
  B) Store del cue con la seleccion del cue anterior intacta (duplicaria)
  C) Clear + Store y se mira si el cue queda vacio o con los valores previos

Verificacion: export + XML, unico read-back fiable.
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
SEQ = 170


def cues_del_xml(nombre):
    ruta = EXPORT_DIR / f"{nombre}.xml"
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    out = {}
    for cue in root.iter(f"{NS}Cue"):
        idx = cue.get("index")
        if idx is None:
            continue
        vals = []
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            if ch is not None:
                vals.append(f"fx{ch.get('fixture_id')}."
                            f"{ch.get('attribute_name')}="
                            f"{va.text if va is not None else '-'}")
        out[int(idx)] = vals
    return out


async def exportar(ma2, tag):
    await ma2.cmd("cd /")
    r = await ma2.cmd(f'Export Sequence {SEQ} "{tag}"')
    return r


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {SEQ}")

        # --- cue 1 con valores de referencia (valores distinguibles)
        print("#" * 78)
        print("# cue 1 de referencia: fx23-30 rojo al 40")
        for c in ["Fixture 23 Thru 30",
                  'Attribute "ColorRGB1" At 100',
                  'Attribute "ColorRGB2" At 0',
                  'Attribute "ColorRGB3" At 0',
                  "At 40",
                  f"Store Cue 1 Sequence {SEQ} /noconfirm"]:
            r = await ma2.cmd(c)
            print(f"  {c:<44} {'ok' if not r.errors else 'ERR ' + str(r.errors)}")

        await exportar(ma2, "hold")
        d = cues_del_xml("hold")
        print(f"  cues presentes: {sorted(d.keys()) if d else None}")
        if d:
            print(f"  cue1 tiene {len(d.get(1, []))} valores")

        # --- A) Clear + Store del cue 2
        print()
        print("#" * 78)
        print("# A) Clear (deseleccionar) + Store Cue 2 sin /merge")
        for c in ["cd /", "Clear", f"Store Cue 2 Sequence {SEQ} /noconfirm"]:
            r = await ma2.cmd(c)
            print(f"  {c:<44} {'ok' if not r.errors else 'ERR ' + str(r.errors)}")
        await exportar(ma2, "hold2")
        d2 = cues_del_xml("hold2")
        print(f"  cues presentes: {sorted(d2.keys()) if d2 else None}")
        if d2:
            print(f"  cue2 -> {d2.get(2, [])[:6]}  ({len(d2.get(2, []))} valores)")
            print(f"  {'*** CUE 2 CREADO Y VACIO ***' if 2 in d2 and not d2[2] else ''}")

        # --- B) Store del cue 3 con la seleccion todavia activa
        print()
        print("#" * 78)
        print("# B) Store Cue 3 SIN limpiar la seleccion (deberia duplicar)")
        for c in ["cd /", f"Store Cue 3 Sequence {SEQ} /noconfirm"]:
            r = await ma2.cmd(c)
            print(f"  {c:<44} {'ok' if not r.errors else 'ERR ' + str(r.errors)}")
        await exportar(ma2, "hold3")
        d3 = cues_del_xml("hold3")
        print(f"  cues presentes: {sorted(d3.keys()) if d3 else None}")
        if d3 and 3 in d3:
            print(f"  cue3 -> {len(d3[3])} valores "
                  f"{'(duplico) OK si >0' if d3[3] else '(vacio)'}")

        await ma2.cmd("cd /")
        await ma2.cmd(f"Delete Sequence {SEQ}")
        print(f"\nsecuencia {SEQ} de prueba borrada")


if __name__ == "__main__":
    asyncio.run(main())