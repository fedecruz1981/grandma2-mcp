r"""
Arma el XML de cada escena desde data/plan.json, lo importa y lo verifica.

Metodo elegido por el operador: generar el XML completo e importarlo con
`Import "archivo" At Sequence N` (ver import_test.py: round-trip identico).
Ventaja sobre mandar comandos: los effects entran SIEMPRE, incluso donde
`At Effect N` falla (dimmer en fx23-30, arcoiris en la rueda de los cabezales).

Escenas -> secuencias (una secuencia por escena):
  escena 1 -> seq 156 -> executor 3.101
  ...
  escena 6 -> seq 161 -> executor 3.106

Dentro de cada secuencia los cues se renumeran 1..N (Q1..Q5 = cues 1..5 de la 156).

Uso:
  python scripts\build_sequences.py --dry              # solo muestra el plan
  python scripts\build_sequences.py --escena 2         # graba solo la escena 2
  python scripts\build_sequences.py                    # graba las 6 escenas
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seqxml  # noqa: E402
from ma2_telnet import Ma2  # noqa: E402

DATA = HERE.parent / "data"
EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
SEQ_BASE = 155          # escena 1 -> 156
ORDEN = ["CM", "BT", "FRONT", "BM", "BF", "COB"]


def pct(v):
    return round(v / 255 * 100, 1)


def nombre_de_escena(s):
    """'ESCENA 1 - POR VOS' -> 'E1 POR VOS' (como ya esta la 156)."""
    m = re.match(r"ESCENA\s+(\d+)\s*-\s*(.+)", s, re.I)
    return f"E{m.group(1)} {m.group(2).strip()}" if m else s


def entradas_de_cue(c, con_efecto=frozenset()):
    """Devuelve lista de (fx, attr, valor, (efecto_id, idx, n_fx) | None, stomp).

    `con_efecto` son los (fx, attr) que tenian efecto corriendo desde un cue
    ANTERIOR de la misma secuencia. Ahi va STOMP: sin el flag, un valor fijo se
    mete debajo del efecto que quedo corriendo y el efecto de cambio de color
    sigue por arriba (el efecto "colgado" en los LED). El flag se escribe solo
    cuando el cue actual NO lleva efecto en ese atributo: si lo lleva, el
    efecto nuevo ya pisa al viejo y el stomp sobra.

    Aclaracion: el stomp es el macro 6 "Stomp running Effects" de la consola
    (ClearSelection + Stomp PresetType Thru). No existe como atributo `stomp`
    en el XML: se probaron cuatro grafias (atributo en Value, en CueData, en
    Cue, y el elemento <Stomp/>) y la consola las descarto en silencio. La forma
    real que guarda la consola es <EffectFlags form_index="0"
    sub_form_index="0" />, averiguado en scripts/probar_stomp_en_secuencia.py.
    """
    datos = {}          # (fx, attr) -> [valor, efectoTupla]

    def put(fx, attr, valor=None, efecto=None):
        d = datos.setdefault((fx, attr), [None, None])
        if valor is not None:
            d[0] = valor
        if efecto is not None:
            d[1] = efecto

    for g in ORDEN:
        cg = c["grupos"].get(g)
        if not cg or cg["accion"] == "nada":
            continue
        ini, fin = seqxml.GRUPOS[g]
        fxs = list(range(ini, fin + 1))

        # ---- color
        if g == "CM":
            nombre = cg.get("color") or ""
            rueda_alt = cg.get("rueda_alt")
            if rueda_alt:
                # Un color de RUEDA por fixture. Los cabezales (Beamer 250
                # Mini) NO tienen RGB: su color vive en COLOR1, la rueda. Por
                # eso el "arcoiris" se arma cyclando posiciones de la rueda, una
                # por cabezal, y no con COLORRGB1/2/3 como el resto de los
                # grupos. Sin esto no hay forma de que 4 cabezales muestren 4
                # colores distintos.
                for i, fx in enumerate(fxs):
                    col = rueda_alt[i % len(rueda_alt)]
                    if col not in seqxml.RUEDA:
                        raise SystemExit(
                            f"ERROR: {c['cue']} CM pide rueda_alt {col!r} que no "
                            f"esta en seqxml.RUEDA (fallo silencioso: el "
                            f"cabezal se quedaria con el color anterior).")
                    pos = seqxml.RUEDA[col]
                    if pos is not None:
                        put(fx, "COLOR1", pos)
            elif not (cg.get("alternar_rgb") or cg.get("attrs")):
                if nombre not in seqxml.RUEDA:
                    raise SystemExit(
                        f"ERROR: {c['cue']} grupo CM pide color {nombre!r} que "
                        f"no esta en seqxml.RUEDA. Sin esto la consola se "
                        f"quedaria con el color del cue anterior (fallo "
                        f"silencioso). Agregalo a la RUEDA.")
                rueda = seqxml.RUEDA.get(nombre)
                if rueda is not None:
                    for fx in fxs:
                        put(fx, "COLOR1", rueda)
        elif cg.get("alternar_rgb"):
            # Patron intercalado: un color por fixture, ciclando la lista.
            alt = cg["alternar_rgb"]
            for i, fx in enumerate(fxs):
                rgb = alt[i % len(alt)]
                put(fx, "COLORRGB1", pct(rgb[0]))
                put(fx, "COLORRGB2", pct(rgb[1]))
                put(fx, "COLORRGB3", pct(rgb[2]))
        else:
            rgb = cg.get("rgb")
            if rgb:
                for fx in fxs:
                    put(fx, "COLORRGB1", pct(rgb[0]))
                    put(fx, "COLORRGB2", pct(rgb[1]))
                    put(fx, "COLORRGB3", pct(rgb[2]))

        # ---- nivel y shutter
        if cg.get("dim") is not None:
            for fx in fxs:
                put(fx, "DIM", cg["dim"])
        if cg.get("shutter") is not None:
            for fx in fxs:
                put(fx, "SHUTTER", cg["shutter"])

        # ---- atributos literales extra (ej. COB: su color "CALIDO" vive en
        # COLORRGB18/COLORRGB5, no en RGB1/2/3; ver preset 4.18 del show)
        for attr, val in (cg.get("attrs") or {}).items():
            for fx in fxs:
                put(fx, attr, val)

        # ---- posicion PAN/TILT de los cabezales
        # El operador pidio "10 de pan y tilt" para que no queden todos
        # apuntando al mismo lado. OJO: un valor de PAN/TILT en una secuencia
        # es una POSICION ABSOLUTA, no un desplazamiento. Antes de este cambio
        # no habia ningun PAN/TILT guardado en el show (verificado: 0 valores
        # en las sec 45, 1 y 156), o sea que las secuencias NO manejaban la
        # posicion: los cabezales se quedaban donde los dejara el show. Al
        # escribir valores, la secuencia pasa a apuntarlos de verdad.
        # `pt` es una lista de (pan, tilt) por fixture, en orden fx1..fxN.
        # Con efecto (ef17) en el mismo atributo, manda el efecto y el valor
        # estatico queda como referencia; sin efecto, el valor ES la posicion.
        pt = cg.get("pt")
        if pt:
            for i, fx in enumerate(fxs):
                par = pt[i % len(pt)]
                put(fx, "PAN", par[0])
                put(fx, "TILT", par[1])

        # ---- effect principal (sustituyendo el que el fixture no soporta)
        ef = cg.get("efecto")
        if ef:
            if g == "CM":
                ef = seqxml.CM_EFFECT_SUSTITUTO.get(ef, ef)
            tipo = seqxml.EFECTOS[ef][1]
            n = len(fxs)
            if tipo == "rgb" and g in seqxml.CON_RGB:
                for i, fx in enumerate(fxs):
                    put(fx, "COLORRGB1", None, (ef, i, n))
                    put(fx, "COLORRGB2", None, (ef, i, n))
                    put(fx, "COLORRGB3", None, (ef, i, n))
            elif tipo == "pt":
                for i, fx in enumerate(fxs):
                    put(fx, "PAN", None, (ef, i, n))
                    put(fx, "TILT", None, (ef, i, n))
            elif tipo == "shutter":
                # El ef6 va sobre SHUTTER, salvo en los grupos sin shutter
                # animable (BM, fx15-22) donde se manda sobre DIM: la consola
                # descarta el CueData de SHUTTER y el strobo se pierde.
                # Ver seqxml.SIN_SHUTTER y scripts/test_strobe_bm2.py.
                attr = seqxml.atributo_de_efecto(g, ef) or "SHUTTER"
                for fx in fxs:
                    if attr == "SHUTTER":
                        put(fx, attr, 0 if cg.get("shutter") is None
                            else cg["shutter"], (ef, 0, n))
                    else:
                        # DIM ya tiene su valor puesto: solo se le suma el efecto
                        put(fx, attr, None, (ef, 0, n))
            else:                                   # dim
                for fx in fxs:
                    put(fx, "DIM", None, (ef, 0, n))

        # ---- strobo ("stomps"): el operador pidio que no se pierda ninguno.
        # El PDF lo menciona como algo secundario ("algun strobo suave"). Va
        # sobre SHUTTER, asi que NO pisa el barrido (que va sobre color o PAN/TILT).
        b = (cg.get("bruto") or "").lower()
        if ("strob" in b or "stomp" in b) and "sin strob" not in b and ef != 6:
            attr = seqxml.atributo_de_efecto(g, 6) or "SHUTTER"
            for fx in fxs:
                if attr == "SHUTTER":
                    put(fx, attr, 0 if cg.get("shutter") is None
                        else cg["shutter"], (6, 0, len(fxs)))
                else:
                    put(fx, attr, None, (6, 0, len(fxs)))

    # ---- stomp: pisar los efectos que venian corriendo de antes
    salidas = []
    for (fx, attr), d in sorted(datos.items()):
        valor, efecto = d[0], d[1]
        stomp = (efecto is None and valor is not None
                 and (fx, attr) in con_efecto)
        salidas.append((fx, attr, valor, efecto, stomp))
    con_efecto_nuevo = set(con_efecto)
    for (fx, attr), d in datos.items():
        if d[1] is not None:
            con_efecto_nuevo.add((fx, attr))
        elif d[0] is not None:
            con_efecto_nuevo.discard((fx, attr))
    entradas_de_cue.ultimo_con_efecto = frozenset(con_efecto_nuevo)
    return salidas


def _n(v):
    """Normaliza un valor para comparar: la consola guarda 100 y 83.900002
    donde nosotros escribimos 100.0 y 83.9."""
    if v is None:
        return None
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return v


def resumen_xml(ruta):
    if not ruta.exists():
        return None
    root = ET.parse(ruta).getroot()
    out = {}
    for cue in root.iter(f"{NS}Cue"):
        ci = cue.get("index")
        if ci is None:
            continue
        filas = set()
        for cd in cue.iter(f"{NS}CueData"):
            ch = cd.find(f"{NS}Channel")
            va = cd.find(f"{NS}Value")
            ef = cd.find(f"{NS}Effect")
            if ch is None:
                continue
            filas.add((int(ch.get("fixture_id")), ch.get("attribute_name"),
                       _n(va.text if va is not None else None),
                       ef.get("name") if ef is not None else None))
        out[int(ci)] = filas
    return out


def resumen_plan(cues):
    """Lo mismo pero desde lo que vamos a escribir (para comparar)."""
    out = {}
    for numero, entradas in cues:
        filas = set()
        for entrada in entradas:
            fx, attr, valor, efectoT = entrada[:4]
            enombre = None
            if efectoT:
                eid = efectoT[0]
                enombre = f"{seqxml.EFECTOS[eid][0]} {eid}"
            # un valor stompeado llega a la consola como Value + EffectFlags
            # form_index=0 y SIN <Effect>, asi que enombre queda None y el
            # round-trip sigue cuadrando. El flag se verifica aparte, en
            # scripts/ver_stomps.py.
            filas.add((fx, attr, _n(valor), enombre))
        out[numero] = filas
    return out


async def importar(ma2, nombre, target):
    """Importa y contesta Overwrite si la secuencia ya existe.

    Medido (import_overwrite_test.py): Import sobre una secuencia existente abre
    el dialogo `Overwrite Confirmation`; sin contestarlo, el comando siguiente se
    come como respuesta. Contestar 1 = Overwrite (reemplaza toda la secuencia).
    """
    await ma2.cmd("cd /")
    r = await ma2.cmd(f'Import "{nombre}" At Sequence {target}')
    if "Overwrite Confirmation" in "\n".join(r.lines):
        r = await ma2.cmd("1")
    return r


async def exportar(ma2, seq, tag):
    """Exporta y espera el archivo (la escritura no es instantanea)."""
    ruta = EXPORT_DIR / f"{tag}.xml"
    if ruta.exists():
        ruta.unlink()
    await ma2.cmd("cd /")
    await ma2.cmd(f'Export Sequence {seq} "{tag}"')
    for _ in range(15):
        if ruta.exists() and ruta.stat().st_size > 0:
            return resumen_xml(ruta)
        await asyncio.sleep(0.3)
    return None


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--escena", type=int, help="grabar solo esta escena")
    ap.add_argument("--escenas", help="grabar varias escenas, ej. 1,3,4,5,6")
    ap.add_argument("--seq-destino", type=int,
                    help="probar la escena en OTRA secuencia (scratch); no guarda")
    ap.add_argument("--dry", action="store_true", help="no manda nada")
    args = ap.parse_args()

    plan = json.loads((DATA / "plan.json").read_text(encoding="utf-8"))
    escenas = []
    for c in plan:
        if c["scene"] not in escenas:
            escenas.append(c["scene"])
    print(f"escenas: {len(escenas)}  cues: {len(plan)}")

    varias = {int(x) for x in args.escenas.split(",")} if args.escenas else set()
    objetivos = []
    for i, esc in enumerate(escenas, 1):
        if args.escena and i != args.escena:
            continue
        if varias and i not in varias:
            continue
        cues_esc = [c for c in plan if c["scene"] == esc]
        cues = []
        # se arrastra de cue a cue que (fx, attr) tienen efecto corriendo, para
        # poder escribir STOMP en el cue que lo pisa
        con_efecto = frozenset()
        for j, c in enumerate(cues_esc, 1):
            ents = entradas_de_cue(c, con_efecto)
            con_efecto = entradas_de_cue.ultimo_con_efecto
            cues.append((j, ents))
        seq = SEQ_BASE + i
        if args.seq_destino and args.escena and i == args.escena:
            seq = args.seq_destino
        objetivos.append((i, esc, seq, cues))

    for i, esc, seq, cues in objetivos:
        n_ef = sum(1 for _, ents in cues
                   for e in ents if e[3])
        n_val = sum(1 for _, ents in cues
                    for e in ents if e[2] is not None)
        n_stomp = sum(1 for _, ents in cues
                      for e in ents if e[4] if len(e) > 4)
        print(f"\n  escena {i}: {esc!r}")
        print(f"    seq {seq}  {nombre_de_escena(esc)!r}  "
              f"cues 1-{len(cues)}  valores={n_val}  effects={n_ef}"
              f"  stomps={n_stomp}")

    if args.dry:
        return

    async with Ma2() as ma2:
        await ma2.at_prompt()
        for i, esc, seq, cues in objetivos:
            nombre = nombre_de_escena(esc)
            # OJO: <Sequ index> = numero_de_secuencia - 1 (medido en los exports).
            xml = seqxml.secuencia(seq - 1, nombre, cues)
            archivo = EXPORT_DIR / f"build_{seq}.xml"
            archivo.write_text(xml, encoding="utf-8")
            print(f"\n=== escena {i} -> seq {seq} {nombre!r}  "
                  f"({len(xml)} bytes)")
            r = await importar(ma2, f"build_{seq}", seq)
            for ln in [x for x in r.body if x.strip()][-2:]:
                print(f"    {ln.strip()[:130]}")
            await ma2.cmd("cd /")
            await ma2.cmd(f"Label Sequence {seq} \"{nombre}\"")
            await ma2.cmd("cd /")
            obtenido = await exportar(ma2, seq, f"chk_{seq}")
            if obtenido is None:
                print("    ERROR: no se pudo exportar para verificar")
                continue

            esperado = resumen_plan(cues)
            faltan = sobra = 0
            for cn in esperado:
                a, b = esperado[cn], obtenido.get(cn, set())
                falta = a - b
                extra = b - a
                if falta:
                    faltan += len(falta)
                    print(f"    cue {cn} FALTA: {sorted(falta)[:4]}")
                if extra:
                    sobra += len(extra)
                    print(f"    cue {cn} SOBRA: {sorted(extra)[:4]}")
            estado = "OK" if not faltan and not sobra else "REVISAR"
            print(f"    VERIFICACION {estado}: cues={sorted(obtenido)}  "
                  f"faltan={faltan}  sobran={sobra}")

        if args.seq_destino:
            print("\n  (modo scratch: no se guarda el show)")
        else:
            await ma2.cmd("cd /")
            r = await ma2.cmd("SaveShow /noconfirm")
            for ln in [x for x in r.body if x.strip()][:2]:
                print(f"\n  {ln.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
