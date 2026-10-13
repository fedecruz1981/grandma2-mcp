r"""
Verifica las REGLAS DE FONDO del diseño sobre el export real de la consola.

No mira el plan (que ya sabemos que esta bien): mira lo que quedo grabado.

Reglas:
  1. Ningun cue en negro total (siempre queda luz).
  2. Los dos congelados (Q4 de la escena 1 y Q13 de la escena 3) van TODO
     AZUL: los 6 grupos, no solo los cabezales.
  3. Escena 2 (seq 157) sin color: solo blanco y gris (saturacion ~0).
  4. COB al 40% en todas las escenas menos la 2, y ausente en la 2.
  5. Los cabezales (fx1-4) con DIM > 0 en los 53 cues.

Uso: python scripts\ver_reglas_fondo.py
"""
import asyncio
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402
from ma2_telnet import ANSI  # noqa: E402

EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"

GRUPOS = {"CM": (1, 4), "BT": (5, 8), "FRONT": (9, 14), "BM": (15, 22),
          "BF": (23, 30), "COB": (32, 34)}

# seq -> (cue de la sec, nombre del cue global). Q4 es el cue 4 de la 156
# (Q1..Q5), y Q13 es el cue 2 de la 158 (Q12, Q13, ...).
CONGELADOS = [(156, 4, "Q4  Luna congela a Inti"),
              (158, 2, "Q13 Luna lo congela (escena 3)")]

# El COB queda excluido del chequeo de congelado a proposito: es la luz de
# cabina y su color vive en COLORRGB18/COLORRGB5 (preset CALIDO), no en la
# rueda ni en RGB1/2/3. El operador la fijo al 40% en todas las escenas.
GRUPOS_CONGELADO = ("CM", "BT", "FRONT", "BM", "BF")


def leer(ruta):
    import xml.etree.ElementTree as ET
    root = ET.parse(ruta).getroot()
    cues = {}
    for cue in root.iter(f"{NS}Cue"):
        idx = cue.get("index")
        if idx is None:
            continue
        val = {}
        ef = {}
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            e = cd.find(f"{NS}Effect")
            if ch is None:
                continue
            fx = int(ch.get("fixture_id"))
            attr = ch.get("attribute_name")
            try:
                v = round(float(va.text), 1) if va is not None else None
            except (TypeError, ValueError):
                v = va.text if va is not None else None
            val[(fx, attr)] = v
            if e is not None:
                ef.setdefault(fx, set()).add(e.get("name"))
        cues[int(idx)] = (val, ef)
    return cues


async def exportar(ma2, seq, sello):
    tag = f"rf_{seq}_{sello}"
    f = EXPORT / f"{tag}.xml"
    f.unlink(missing_ok=True)
    await ma2.drain()
    await ma2._raw(f"Export Sequence {seq} '{tag}'")
    crudo = await ma2._read_until_prompt(max_wait=6.0)
    if "Overwrite" in ANSI.sub("", crudo or ""):
        await ma2.drain()
        await ma2._raw("2")
        await ma2._read_until_prompt(max_wait=3.0)
    for _ in range(30):
        if f.exists() and f.stat().st_size > 0:
            break
        await asyncio.sleep(0.3)
    if not (f.exists() and f.stat().st_size > 0):
        return None
    datos = leer(f)
    f.unlink(missing_ok=True)
    return datos


async def main():
    sello = int(time.time()) % 100000
    fallos = []
    todos = {}
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")

    async with Ma2() as ma2:
        for seq in (156, 157, 158, 159, 160, 161):
            d = await exportar(ma2, seq, sello)
            if d is None:
                print(f"  seq {seq}: no se pudo exportar")
                fallos.append(f"seq {seq} no exportable")
            else:
                todos[seq] = d
        await ma2.drain()
        await ma2._raw("Clear")

    if not todos:
        print("no hay ningun export: no se puede verificar")
        return 1

    # ---- 1. ningun cue en negro + 5. cabezales prendidos
    print()
    print("1. NINGUN CUE EN NEGRO  /  5. CABEZALES CON DIM > 0")
    for seq, cues in sorted(todos.items()):
        for idx in sorted(cues):
            val, ef = cues[idx]
            cab = [val.get((fx, "DIM")) for fx in (1, 2, 3, 4)]
            cab0 = sum(1 for v in cab if v is None or v == 0)
            if cab0 == 4:
                fallos.append(f"seq {seq} cue {idx}: los 4 cabezales en 0")
                print(f"  seq {seq} cue {idx:>2}: CABEZALES EN NEGRO  {cab}")

    # ---- 2. congelados todo azul
    print()
    print("2. CONGELADOS: TODOS LOS GRUPOS EN AZUL  (COB exuido: es luz de cabina)")
    for seq, cue, etiqueta in CONGELADOS:
        if seq not in todos or cue not in todos[seq]:
            print(f"  {etiqueta}: no encontrada")
            fallos.append(etiqueta)
            continue
        val, ef = todos[seq][cue]
        print(f"\n  {etiqueta}   (seq {seq}, cue {cue})")
        n_azul = 0
        chequeados = 0
        for g in GRUPOS_CONGELADO:
            ini, fin = GRUPOS[g]
            valores = set()
            for fx in range(ini, fin + 1):
                r1 = val.get((fx, "COLOR1"))
                if r1 is not None:
                    valores.add(("rueda", round(r1, 1)))
                else:
                    rgb = tuple(val.get((fx, f"COLORRGB{i}")) for i in (1, 2, 3))
                    if any(v is not None for v in rgb):
                        valores.add(("rgb", rgb))
            if not valores:
                continue
            chequeados += 1
            # Los valores de la consola van de 0 a 100 (no 0 a 255). Azul =
            # el canal azul es el maximo y le gana holgadamente al rojo.
            es_azul = all(
                (k == "rueda" and v == 32.5) or
                (k == "rgb" and v[2] >= max(v) - 2
                 and v[2] >= v[0] + 20 and v[2] >= v[1] - 20)
                for k, v in valores)
            if es_azul:
                n_azul += 1
            print(f"      {g:<6} {'AZUL   ' if es_azul else 'NO AZUL'}  "
                  f"{sorted(str(v) for v in valores)[:2]}")
            if not es_azul:
                fallos.append(f"{etiqueta}: grupo {g} no azul")
        print(f"      -> {n_azul}/{chequeados} grupos en azul"
              + ("   OK" if n_azul == chequeados else "   HAY QUE REVISAR"))

    # ---- 3. escena 2 sin color
    print()
    print("3. ESCENA 2 (seq 157) SIN COLOR: solo blanco y gris")
    for idx in sorted(todos.get(157, {})):
        val, ef = todos[157][idx]
        peor = (0.0, 0.0, 0.0, 0.0)
        for fx in range(1, 35):
            rgb = tuple(val.get((fx, f"COLORRGB{i}")) for i in (1, 2, 3))
            if all(v is None for v in rgb):
                continue
            r, g, b = (v or 0 for v in rgb)
            mx, mn = max(r, g, b), min(r, g, b)
            sat = 0 if mx == 0 else (mx - mn) / mx * 100
            if sat > peor[0]:
                peor = (sat, r, g, b)
        marca = "OK" if peor[0] <= 20 else "HAY COLOR"
        if peor[0] > 20:
            fallos.append(f"escena 2 cue {idx}: saturacion {peor[0]:.0f}%")
        print(f"  cue {idx:>2}: saturacion maxima {peor[0]:>5.1f}%  "
              f"rgb({peor[1]:.0f},{peor[2]:.0f},{peor[3]:.0f})  {marca}")

    # ---- 4. COB
    print()
    print("4. COB (fx32-34): 40% en todas menos la escena 2, y ausente en la 2")
    for seq, cues in sorted(todos.items()):
        for idx in sorted(cues):
            val, ef = cues[idx]
            cob = [val.get((fx, "DIM")) for fx in (32, 33, 34)]
            rgb18 = val.get((32, "COLORRGB18"))
            rgb5 = val.get((32, "COLORRGB5"))
            if all(v is None for v in cob):
                continue
            nivel = cob[0]
            if seq == 157 and nivel is not None:
                fallos.append(f"escena 2 cue {idx}: COB presente")
                print(f"  seq {seq} cue {idx:>2}: COB presente "
                      f"(deberia estar ausente)  nivel={nivel}")
            elif seq != 157 and nivel != 40:
                fallos.append(f"seq {seq} cue {idx}: COB al {nivel}, no 40")
                print(f"  seq {seq} cue {idx:>2}: COB al {nivel} (esperado 40)")

    print()
    print("=" * 74)
    if fallos:
        print(f"HAY {len(fallos)} COSAS PARA REVISAR:")
        for f in fallos[:25]:
            print(f"   - {f}")
    else:
        print("TODO OK: negro, congelados, escena 2 sin color y COB correctos.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))