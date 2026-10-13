"""
Graba una escena del plan en una secuencia de la consola, y la verifica.

Decisiones del operador aplicadas:
  - nivel por defecto 100% en las celdas sin porcentaje (que las baje a mano)
  - fx9-14 (Flat 210) derivados de BF al 45%
  - SHUTTER abierto/cerrado se escribe (0 abierto / 100 cerrado)
  - CM se graba con color + nivel asumido

LIMITE DURO: los effects NO se pueden escribir por telnet (effect_test2.py,
7 variantes, todas no-op). Los cues con effect quedan grabados con su color y
nivel, y el effect hay que cargarlo en la consola. Queda listado en el reporte.

Sintaxis verificada con store+export (scripts/sel_test3.py, effect_test.py,
    hold_test.py):
    Fixture 23 Thru 30            selecciona el rango (SIN sufijo de unidad:
                                   `Fixture 23.1 Thru 30.1` da ILLEGAL RANGE)
    Attribute "ColorRGB1" At 100  setea atributo por nombre de libreria
    Attribute "Shutter" At 0
    At 70                         setea el dimmer
    Clear                         vacia el programador y deselecciona
    Store Cue 1 Sequence 156 /noconfirm          crea la secuencia si no existe

Clear va PRIMERO en cada cue a proposito: si no, el store puede capturar los
valores que quedo del cue anterior con la seleccion vieja. Con Clear, el
programador solo contiene lo de este cue, y `Store Cue N` sin /merge deja el
cue con exactamente esos valores. Eso hace que re-grabar una escena sea
idempotente, y que un cue de hold (celdas con guion largo) quede VACIO de
verdad y no con duplicados.

Uso:
  python scripts/record_scene.py 1 156          # escena 1 -> secuencia 156
  python scripts/record_scene.py 1 156 --dry    # solo muestra, no escribe
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402
from translate import GRUPOS, pct_rgb  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"

# nombre corto para el export de verificacion
EXPORT_TAG = "verif"


def num_cue(q):
    return int(q[1:])


def comandos_de_grupo(nombre, ini, fin, r):
    """
    Comandos para setear un grupo. Devuelve lista de strings.

    Solo se escribe lo que tiene valor resuelto: una celda 'nada' no genera
    ningun comando, para no pisar el tracking con valores inventados.
    """
    cmds = []
    if r["rgb"] is None and r["dim"] is None and r["shutter"] is None:
        return cmds

    sel = (f"Fixture {ini}" if ini == fin else f"Fixture {ini} Thru {fin}")
    cmds.append(sel)
    if r["rgb"]:
        cmds.append(f'Attribute "ColorRGB1" At {pct_rgb(r["rgb"][0])}')
        cmds.append(f'Attribute "ColorRGB2" At {pct_rgb(r["rgb"][1])}')
        cmds.append(f'Attribute "ColorRGB3" At {pct_rgb(r["rgb"][2])}')
    if r["shutter"] is not None:
        cmds.append(f'Attribute "Shutter" At {r["shutter"]}')
    if r["dim"] is not None:
        cmds.append(f"At {r['dim']}")
    return cmds


def leer_export(nombre):
    """{(cue, fixture, atributo): valor} del xml exportado."""
    ruta = EXPORT_DIR / f"{nombre}.xml"
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    out = {}
    for cue in root.iter(f"{NS}Cue"):
        idx = cue.get("index")
        if idx is None:
            continue
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            if ch is None:
                continue
            out[(int(idx), int(ch.get("fixture_id")),
                 ch.get("attribute_name"))] = (
                va.text if va is not None else None)
    return out


def cues_presentes(nombre):
    """Set de indices de cue que existen en el xml exportado."""
    ruta = EXPORT_DIR / f"{nombre}.xml"
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    return {int(c.get("index")) for c in root.iter(f"{NS}Cue")
            if c.get("index") is not None}


def esperado_para(plan, fila, cue_num):
    """{(cue, fixture, atributo): valor} que deberia quedar en el show."""
    exp = {}
    for g, ini, fin, _ in GRUPOS:
        r = fila["grupos"].get(g)
        if not r:
            continue
        for fx in range(ini, fin + 1):
            if r["rgb"]:
                for k, comp in enumerate(("COLORRGB1", "COLORRGB2",
                                         "COLORRGB3")):
                    exp[(cue_num, fx, comp)] = pct_rgb(r["rgb"][k])
            if r["shutter"] is not None:
                exp[(cue_num, fx, "SHUTTER")] = r["shutter"]
            if r["dim"] is not None:
                exp[(cue_num, fx, "DIM")] = r["dim"]
    return exp


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("escena", type=int)
    ap.add_argument("secuencia", type=int)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    plan = json.loads((DATA / "plan.json").read_text(encoding="utf-8"))
    sel = [f for f in plan if f["scene"].startswith(f"ESCENA {args.escena}")]
    sel.sort(key=lambda f: num_cue(f["cue"]))
    if not sel:
        print(f"no hay cues para ESCENA {args.escena}")
        return

    total_cmds = 0
    for fila in sel:
        for g, ini, fin, _ in GRUPOS:
            r = fila["grupos"].get(g)
            if r and (r["rgb"] or r["dim"] is not None or
                      r["shutter"] is not None):
                total_cmds += len(comandos_de_grupo(g, ini, fin, r))

    print(f"ESCENA {args.escena} -> secuencia {args.secuencia}")
    print(f"  {len(sel)} cues, ~{total_cmds} comandos"
          f"{'  [DRY RUN: no se escribe]' if args.dry else ''}\n")

    if args.dry:
        for fila in sel:
            n = num_cue(fila["cue"])
            for g, ini, fin, _ in GRUPOS:
                r = fila["grupos"].get(g)
                cmds = comandos_de_grupo(g, ini, fin, r) if r else []
                print(f"  cue{n} {g:<6} {len(cmds)} cmd(s): "
                      f"{' ; '.join(cmds) if cmds else '(nada)'}")
        return

    errores = []
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for idx, fila in enumerate(sel):
            n = num_cue(fila["cue"])
            print("=" * 78)
            print(f"{fila['cue']}  {fila['momento']}")
            cmds = []
            for g, ini, fin, _ in GRUPOS:
                r = fila["grupos"].get(g)
                if r:
                    cmds.extend(comandos_de_grupo(g, ini, fin, r))

            if not cmds:
                print("  cue de HOLD: celdas con guion largo = no cambiar. "
                      "Se crea vacio para no romper la numeracion del PDF.")

            # Clear primero: el programador queda limpio y este cue solo
            # contiene lo que se setea aqui.
            r = await ma2.cmd("Clear")
            if r.errors:
                errores.append((fila["cue"], "Clear", r.errors))

            for c in cmds:
                r = await ma2.cmd(c)
                if r.errors:
                    errores.append((fila["cue"], c, r.errors))
                    print(f"  ERR {c} -> {r.errors}")

            store = f"Store Cue {n} Sequence {args.secuencia} /noconfirm"
            r = await ma2.cmd(store)
            print(f"  {len(cmds)} valores + {store}")
            if r.errors:
                errores.append((fila["cue"], store, r.errors))
                print(f"  ERR {store} -> {r.errors}")

    # ------------------------------------------------------------ verificar
    print("\n" + "=" * 78)
    print("VERIFICACION: se exporta la secuencia y se compara con el plan")
    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ma2.cmd("cd /")
        r = await ma2.cmd(f'Export Sequence {args.secuencia} "{EXPORT_TAG}"')
        if r.errors:
            print(f"  fallo el export: {r.errors}")

    real = leer_export(EXPORT_TAG)
    if real is None:
        print("  no se genero el XML de verificacion")
        return

    filas = []
    # 1) el show tiene TODOS los cues del PDF, incluso los de hold
    presentes = cues_presentes(EXPORT_TAG) or set()
    esperados_cue = {num_cue(f["cue"]) for f in sel}
    faltan = sorted(esperados_cue - presentes)
    if faltan:
        filas.append(f"  FALTAN cues en el show: {faltan} "
                     f"(el PDF los tiene, para no romper la numeracion)")
    sobran = sorted(presentes - esperados_cue)
    if sobran:
        filas.append(f"  cues de mas en el show: {sobran}")

    # 2) cada valor del plan esta en el show, con el valor exacto
    for fila in sel:
        n = num_cue(fila["cue"])
        exp = esperado_para(plan, fila, n)
        for (cn, fx, attr), val in sorted(exp.items()):
            got = real.get((cn, fx, attr))
            if got is None:
                filas.append(f"  FALTA  cue{cn} fx{fx} {attr} "
                             f"(esperado {val})")
            elif abs(float(got) - float(val)) > 0.05:
                filas.append(f"  DISTINTO cue{cn} fx{fx} {attr}: "
                             f"show={got} plan={val}")
    # valores en el show que el plan no pedia
    esperados = set()
    for fila in sel:
        n = num_cue(fila["cue"])
        esperados |= set(esperado_para(plan, fila, n).keys())
    for (cn, fx, attr), val in sorted(real.items()):
        if (cn, fx, attr) not in esperados:
            filas.append(f"  SOBRA  cue{cn} fx{fx} {attr}={val} "
                         f"(el plan no lo pidio)")

    if filas:
        print(f"  {len(filas)} diferencia(s):")
        for f in filas[:60]:
            print(f)
        if len(filas) > 60:
            print(f"  ... y {len(filas) - 60} mas")
    else:
        print(f"  OK: los {len(esperados)} valores del plan coinciden "
              f"con el show")

    # pendientes que la consola no puede resolver
    pend = []
    for fila in sel:
        for a in fila["avisos"]:
            pend.append(f"{fila['cue']}: {a}")
    print(f"\n  PENDIENTE A MANO ({len(pend)}):")
    for p in pend:
        print(f"    {p}")
    if errores:
        print(f"\n  ERRORES DE ESCRITURA ({len(errores)}):")
        for c, cmd, e in errores:
            print(f"    {c}: {cmd} -> {e}")


def _grp(fila, g):
    """(ini, fin, r) de un grupo del plan."""
    for nombre, ini, fin, _ in GRUPOS:
        if nombre == g:
            return nombre, ini, fin, fila["grupos"].get(g)
    raise KeyError(g)


def _grp(fila, g):
    """(nombre, ini, fin, r) de un grupo del plan."""
    for nombre, ini, fin, _ in GRUPOS:
        if nombre == g:
            return nombre, ini, fin, fila["grupos"].get(g)
    raise KeyError(g)


if __name__ == "__main__":
    asyncio.run(main())