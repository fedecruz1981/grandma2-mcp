"""
Traduce el cue sheet del PDF a valores de fixture por cue.

Salida: data/plan.json  ->  lo que hay que escribir en la consola.

QUE ESTA VERIFICADO Y QUE NO
----------------------------
Verificado por store+export real en la consola:
    DIM, COLORRGB1 (R), COLORRGB2 (G), COLORRGB3 (B), SHUTTER

Eso es TODO lo que este plan escribe.

NO se puede escribir por telnet:
    effects dentro de un cue. Se probaron 7 variantes de `Assign Effect`
    (con y sin contexto de cue, con destino explicito, con /merge) y las 7
    devuelven "ok" sin guardar nada: el XML exportado no tiene ningun tag
    <Effect>. Ver scripts/effect_test2.py. Por eso los 28 cues con effect y
    las 15 celdas multicolor quedan como PENDIENTE para la consola, y con
    ellos los stomps.

`list attribute` devuelve la lista universal de MA2 (41 atributos, identica
para los 5 tipos de fixture), asi que NO sirve para saber que canales tiene
realmente cada fixture. PAN, TILT, FOCUS, GOBO1 etc. quedan como MANUAL: no
esta verificado que esten patcheados.

Grupos de fixtures (decidido con el operador):
  CM    = fx  1-4   cabezales Beamer 250 Mini
  BT    = fx  5-8   stromber, barra trasera
  FRONT = fx  9-14  Nebula Flat 210, barra frontal
  BM    = fx 15-22  Nebula Max 162, barra media
  BF    = fx 23-30  Protones, barra frontal

Por que reglas explicitas y no NLP difuso: en iluminacion "igual" y un guion
largo no significan lo mismo que en texto. "-" es "no cambiar" (no "apagar"),
y "igual" en BM/BT significa "lo mismo que BF". Interpretar eso mal cambia el
show entero en silencio.

Uso:
  python scripts/translate.py            # genera data/plan.json
  python scripts/translate.py --show 1   # imprime la escena N resuelta
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

# ---------------------------------------------------------------- paleta
# RGB crudo 0-255, a mano, sin presets. La consola guarda en escala 0-100
# (COLORRGB1=R, COLORRGB2=G, COLORRGB3=B); conversion en pct_rgb().
PALETA = {
    "Negro":          (0, 0, 0),
    "Blanco duro":    (255, 255, 255),
    "Blanco frío":    (214, 232, 255),
    "Blanco cálido":  (255, 232, 196),
    "Cálido neutro":  (255, 240, 220),
    "Gris frío":      (196, 202, 208),
    "Gris neutro":    (190, 190, 190),
    "Ámbar cálido":   (255, 160, 20),
    "Ámbar oscuro":   (180, 90, 10),
    "Ámbar tenue":    (210, 120, 30),
    "Dorado":         (255, 190, 60),
    "Rojo":           (255, 0, 0),
    "Rojo oscuro":    (150, 0, 0),
    "Naranja":        (255, 120, 0),
    "Rosa":           (255, 60, 130),
    "Amarillo":       (255, 220, 0),
    "Verde":          (0, 255, 60),
    "Verde suave":    (0, 190, 60),
    "Azul":           (0, 80, 255),
    "Azul cielo":     (120, 200, 255),
    "Azul hielo":     (150, 220, 255),
    "Celeste":        (120, 200, 255),
    "Morado":         (130, 0, 255),
}

# Colores explicitos. Frases largas primero solo como ayuda de lectura; el
# desempate real lo hace el algoritmo por POSICION y solapamiento (mas largo
# gana), no el orden de este diccionario.
COLORES = {
    "blanco duro": "Blanco duro",
    "blanco frio": "Blanco frío",
    "blanco frío": "Blanco frío",
    "blanco calido": "Blanco cálido",
    "blanco cálido": "Blanco cálido",
    "gris frio": "Gris frío",
    "gris frío": "Gris frío",
    "azul hielo": "Azul hielo",
    "azul cielo": "Azul cielo",
    "ambar oscuro": "Ámbar oscuro",
    "ámbar oscuro": "Ámbar oscuro",
    "ambar tenue": "Ámbar tenue",
    "ámbar tenue": "Ámbar tenue",
    "ambar calido": "Ámbar cálido",
    "ámbar cálido": "Ámbar cálido",
    "ambar": "Ámbar cálido",
    "ámbar": "Ámbar cálido",
    "rojo oscuro": "Rojo oscuro",
    "calido neutro": "Cálido neutro",
    "cálido neutro": "Cálido neutro",
    "dorado": "Dorado",
    "naranja": "Naranja",
    "morado": "Morado",
    "celeste": "Celeste",
    "rosa": "Rosa",
    "rojo": "Rojo",
    "amarillo": "Amarillo",
    "verde suave": "Verde suave",
    "verde": "Verde",
    "azul": "Azul",
    "gris": "Gris neutro",
    "blanco": "Blanco duro",
}

# Palabras de TONO. Solo cuentan si la celda NO menciona ningun color:
# en "azul hielo frio" el "frio" refuerza el azul, no pide un blanco frio.
TONO = {
    "frio": "Blanco frío",
    "frío": "Blanco frío",
    "calido": "Blanco cálido",
    "cálido": "Blanco cálido",
    "neutro": "Cálido neutro",
    "neutra": "Cálido neutro",
    "fria": "Blanco frío",
    "fría": "Blanco frío",
    "calida": "Blanco cálido",
    "cálida": "Blanco cálido",
}

# Modificadores de INTENSIDAD sin numero: no fijan nivel, pero avisan de que
# el LD esta describiendo una intensidad relativa que el texto no cuantifica.
INTENSIDAD = ("tenue", "suave", "fuerte", "intenso", "potente", "bajo", "alto")

# Palabras que son MOVIMIENTO en el tiempo: necesitan un effect del pool.
PALABRAS_EFECTO = (
    "chase", "barrido", "barridos", "parpadeo", "strobo", "flash",
    "rotando", "rotacion", "rotación", "multicolor", "sincroniz", "a tempo",
    "golpes", "estribillo", "titila",
)
EFFECT_DE = {
    "chase": 2, "parpadeo": 3, "flash": 3, "titila": 3,
    "strobo": 6, "barrido": 7, "barridos": 7, "rotando": 7,
    "rotacion": 7, "rotación": 7, "multicolor": 7, "sincroniz": 3,
}

# Instrucciones de POSICION: no se pueden resolver desde un cue sheet de texto
# porque dependen de donde esta parado Inti/Luna en ese momento.
POSICION = ("sobre inti", "sobre luna", "sobre ambos", "intenso sobre",
            "apunta", "apuntando", "al centro", "al publico", "al público")

# SHUTTER: SI se puede escribir. Verificado con store+export:
# `Attribute "Shutter" At N` produce <Channel attribute_name="SHUTTER">.
#
# OJO con la convencion: en grandMA el atributo Shutter va 0 = haz ABIERTO y
# 100 = cerrado. Hay que confirmarlo a ojo en el primer cue, porque un cabeceo
# aqui alumbra al reves. Queda en la lista de revision manual por eso.
SHUTTER = {"abierto": 0, "abierta": 0, "cerrado": 100, "cerrada": 100}

# FRONT (fx 9-14) no tiene columna en el PDF: se deriva de BF a este nivel.
FRONT_GAIN = 45

# Nivel por defecto cuando la celda no da porcentaje. ASUMIDO, no deducido:
# esta en una sola linea para poder cambiarlo si el operador decide otra cosa.
DIM_POR_DEFECTO = 100


def pct_rgb(v):
    """0-255 -> 0-100, que es la escala que guarda la consola."""
    return round(v / 255 * 100, 1)


def buscar_color(texto):
    """
    Colores mencionados, en el orden en que aparecen en el texto.

    [(nombre, rgb, inicio, frase)]

    El desempate es POR POSICION: se recogen todos los matches, gana el mas
    largo cuando se solapan ("azul hielo" le gana a "azul"), y se descarta
    cualquier match que pise a uno ya aceptado. Elegir "el del medio de la
    lista" no era correcto: en "Todo a AZUL HIELO frio" eso resolvia a Azul,
    y en "Multicolor calido (rojo/naranja/rosa)" a Rosa, por puro orden.
    """
    t = texto.lower()
    cands = []
    for frase, nombre in COLORES.items():
        for m in re.finditer(
            rf"(?<![a-z0-9áéíóúñ]){re.escape(frase)}(?![a-z0-9áéíóúñ])", t
        ):
            cands.append((m.start(), m.end(), nombre, frase))

    cands.sort(key=lambda c: (-(c[1] - c[0]), c[0]))
    tomados = []
    for ini, fin, nombre, frase in cands:
        if any(not (fin <= a or ini >= b) for a, b, *_ in tomados):
            continue          # pisa a uno mas largo ya aceptado
        tomados.append((ini, fin, nombre, frase))
    tomados.sort(key=lambda c: c[0])

    return [(n, PALETA[n], i, f) for i, _, n, f in tomados]


def buscar_tono(texto, ya_hay_color):
    """Tone fallback: solo si la celda no nombro ningun color."""
    if ya_hay_color:
        return None
    t = texto.lower()
    for palabra, nombre in TONO.items():
        if re.search(rf"(?<![a-z0-9áéíóúñ]){re.escape(palabra)}"
                     rf"(?![a-z0-9áéíóúñ])", t):
            return nombre
    return None


def pct_de(texto):
    """(dim 0-100 o None, texto sin el porcentaje)."""
    m = re.search(r"(\d{1,3})\s*(?:%|pct|por ciento)", texto, re.I)
    if m:
        return max(0, min(100, int(m.group(1)))), \
            texto[:m.start()] + texto[m.end():]
    if re.search(r"\bfull\b|\btodo\b\s*a\s*100", texto, re.I):
        return 100, re.sub(r"\bfull\b", "", texto, flags=re.I)
    return None, texto


def segundos_de(texto):
    """Duracion explicita en segundos: '1 seg', '2 segundos'."""
    m = re.search(r"(\d+)\s*(?:seg|segundo|segundos|s\b)", texto, re.I)
    return int(m.group(1)) if m else None


def resolver(celda, propagar_todo=False):
    """
    Resuelve una celda del PDF a valores de fixture.

    Args:
        celda: texto de la celda
        propagar_todo: True si la celda dice "Todo a X", o sea que el valor
                       vale para TODOS los grupos, no solo para su columna.

    Devuelve dict con:
        accion  'nada'|'apagado'|'igual'|'cambiar'|'propagar'
        dim     0-100, o None si no queda determinado
        color   nombre de paleta, o None
        rgb     (r,g,b) 0-255, o None
        efecto  id de effect del pool, o None
        multicolor  True si la celda nombra mas de un color
        shutter 0-100 si la celda pide abrir/cerrar el haz
        snap    True si pide cambio instantaneo
        segundos duracion explicita, o None
        manual  [instrucciones que el operador tiene que hacer a mano]
        avisos  [observaciones sobre lo asumido]
        bruto   el texto original
    """
    bruto = (celda or "").strip()
    r = {"accion": "nada", "dim": None, "color": None, "rgb": None,
         "efecto": None, "multicolor": False, "shutter": None, "snap": False,
         "segundos": None, "manual": [], "avisos": [], "bruto": bruto}
    if bruto in ("", "-", "—", "–"):
        return r                       # guion largo = NO CAMBIAR, no apagar

    # --- apagado explicito
    if re.fullmatch(r"(?i)\s*(apagad[oa]s?|fade a negro|apagan|negro|"
                    r"se apagan)\s*\.?", bruto):
        r.update(accion="apagado", dim=0)
        return r

    # --- "igual" = copiar el valor de referencia
    if re.fullmatch(r"(?i)\s*igual\.?\s*", bruto):
        r["accion"] = "igual"
        return r

    bajo = bruto.lower()

    # --- "Todo a X": el valor aplica a todos los grupos
    if re.search(r"(?i)\btodo\s+(?:a|el|el rig|en)\b", bajo):
        r["accion"] = "propagar"
    elif propagar_todo:
        r["accion"] = "propagar"

    dim, _ = pct_de(bruto)
    segs = segundos_de(bajo)

    # --- colores
    cols = buscar_color(bruto)
    if not cols:
        tono = buscar_tono(bruto, False)
        if tono:
            cols = [(tono, PALETA[tono], 0, tono)]
    if len(cols) > 1:
        r["multicolor"] = True
        r["efecto"] = EFFECT_DE.get("multicolor")
        r["avisos"].append(
            f"multicolor: nombra {len(cols)} colores "
            f"({', '.join(c[0] for c in cols)}); effect {r['efecto']} "
            f"necesario. Base estatica = {cols[0][0]} (el primero nombrado)")
    if cols:
        # con >1 color el valor estatico es el primero nombrado; el resto lo
        # resuelve el effect. Se declara en avisos, no se elige a ciegas.
        nombre, rgb = cols[0][0], cols[0][1]
        r.update(color=nombre, rgb=rgb)

    # --- efecto por palabra de movimiento
    if not r["efecto"]:
        for p in PALABRAS_EFECTO:
            if p in bajo:
                r["efecto"] = EFFECT_DE.get(p)
                r["avisos"].append(f"effect {r['efecto']} por '{p}'")
                break

    # --- effect: NO se puede escribir. Verificado en effect_test2.py: las 7
    # variantes de `Assign Effect` dan "ok" y no guardan nada (el XML exportado
    # no tiene ningun tag <Effect>). Queda como pendiente para la consola.
    if r["efecto"]:
        r["manual"].append(
            f"effect {r['efecto']} del pool NO se puede escribir por telnet"
            f" -> cargar a mano")

    # --- shutter ("foco abierto" / "haz cerrado"). SI se escribe; el atributo
    # quedo verificado con store+export.
    for palabra, val in SHUTTER.items():
        if re.search(rf"(?<![a-z0-9áéíóúñ]){palabra}(?![a-z0-9áéíóúñ])",
                     bajo):
            r["shutter"] = val
            r["manual"].append(
                f"shutter {palabra} -> {val} (0=abierto/100=cerrado; "
                f"confirmar a la primera)")
            break

    # --- pan/tilt: depende de donde esten los personajes, no se puede resolver
    for p in POSICION:
        if p in bajo:
            r["manual"].append(f"posicion: '{p}' - ajustar pan/tilt a mano")
            break

    # --- intensidad sin numero
    mods = [m for m in INTENSIDAD
            if re.search(rf"(?<![a-z0-9áéíóúñ]){m}(?![a-z0-9áéíóúñ])", bajo)]
    if mods:
        r["avisos"].append(
            f"intensidad relativa '{'/'.join(mods)}' sin numero; "
            f"se asume DIM_POR_DEFECTO={DIM_POR_DEFECTO}")

    r["snap"] = bool(re.search(r"(?i)\bsnap\b", bajo))
    r["segundos"] = segs
    if segs:
        r["manual"].append(f"duracion {segs} seg -> fadeout del cue, no valor")
    if r["snap"]:
        r["manual"].append("'snap' -> fade de atributo 0 en este cue")

    # --- nivel
    if dim is None and (r["rgb"] or r["efecto"]):
        dim = DIM_POR_DEFECTO
        if not mods:
            r["avisos"].append(
                f"celda sin porcentaje; DIM asumido {DIM_POR_DEFECTO}")
    if dim is not None:
        r["dim"] = dim
    if r["accion"] == "propagar":
        r["accion"] = "propagar"
    elif r["rgb"] or r["dim"] is not None or r["efecto"]:
        r["accion"] = "cambiar"
    return r


# ---------------------------------------------------------------- plan
GRUPOS = [
    ("CM",    1, 4,   "cabezales"),
    ("BT",    5, 8,   "barra trasera (stromber)"),
    ("FRONT", 9, 14,  "barra frontal (Flat 210)"),
    ("BM",    15, 22, "barra media (Nebula Max)"),
    ("BF",    23, 30, "barra frontal (Protones)"),
]
COLS_PDF = ("BF", "BM", "BT", "CM")


def construir_plan():
    cues = json.loads((DATA / "pdf_cues.json").read_text(encoding="utf-8"))
    orden = sorted(cues, key=lambda k: int(k[1:]))
    plan = []

    for q in orden:
        c = cues[q]
        fila = {"cue": q, "scene": c["scene"], "momento": c["momento"],
                "grupos": {}, "avisos": []}

        # BF se resuelve primero: es la referencia de "igual" en BM y BT
        ref = resolver(c.get("BF", ""))
        fila["grupos"]["BF"] = ref

        # "Todo a X" en BF propaga a todos los grupos
        propaga = ref["accion"] == "propagar"

        for g in COLS_PDF:
            if g == "BF":
                continue
            celda = c.get(g, "")
            if propaga and celda in ("", "-", "—", "–"):
                r = dict(ref)                      # hereda BF
                r["bruto"] = f"(heredado de BF: {ref['bruto']!r})"
            elif re.fullmatch(r"(?i)\s*igual\.?\s*", (celda or "").strip()):
                r = dict(ref)                      # "igual" = como BF
                r["accion"] = "igual"
                r["bruto"] = f"igual -> {ref['bruto']!r}"
            else:
                r = resolver(celda, propagar_todo=propaga)
            fila["grupos"][g] = r

        # FRONT (fx9-14) no existe en el PDF: derivado de BF
        bf = fila["grupos"]["BF"]
        if bf["rgb"] and bf["dim"] is not None:
            d = round(bf["dim"] * FRONT_GAIN / 100)
            fila["grupos"]["FRONT"] = {
                "accion": "derivado", "dim": d, "color": bf["color"],
                "rgb": bf["rgb"], "efecto": bf["efecto"],
                "multicolor": bf["multicolor"], "shutter": None, "snap": False,
                "segundos": None, "manual": [], "avisos": [], "bruto": "",
            }
        else:
            fila["grupos"]["FRONT"] = {
                "accion": "nada", "dim": None, "color": None, "rgb": None,
                "efecto": None, "multicolor": False, "shutter": None,
                "snap": False, "segundos": None, "manual": [], "avisos": [],
                "bruto": "",
            }

        for g, r in fila["grupos"].items():
            for a in r["avisos"]:
                fila["avisos"].append(f"{g}: {a}")
            for m in r["manual"]:
                fila["avisos"].append(f"{g}: {m}")
        plan.append(fila)
    return plan


def resumen(plan):
    n = len(plan)
    con_efecto = sum(1 for f in plan
                     if any(r["efecto"] for r in f["grupos"].values()))
    multi = sum(1 for f in plan
                if any(r["multicolor"] for r in f["grupos"].values()))
    sin_dim = sum(1 for f in plan for r in f["grupos"].values()
                  if r["rgb"] and r["dim"] is None)
    vacios = sum(1 for f in plan
                 if all(r["accion"] == "nada"
                        for r in f["grupos"].values()))
    return (f"{n} cues | con effect: {con_efecto} | multicolor: {multi} | "
            f"celdas con color sin nivel resuelto: {sin_dim} | "
            f"cues sin ningun valor: {vacios}")


if __name__ == "__main__":
    plan = construir_plan()
    (DATA / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(plan)} cues -> data/plan.json")
    print(resumen(plan))

    if "--show" in sys.argv:
        n = int(sys.argv[sys.argv.index("--show") + 1])
        sel = [f for f in plan if f["scene"].startswith(f"ESCENA {n}")]
        out = []
        for fila in sel:
            out.append("=" * 96)
            out.append(f"{fila['cue']}   {fila['scene']}")
            out.append(f"  momento: {fila['momento']}")
            for g, ini, fin, etq in GRUPOS:
                r = fila["grupos"][g]
                rgb = r["rgb"]
                rp = (f"R{pct_rgb(rgb[0]):>5.1f} G{pct_rgb(rgb[1]):>5.1f} "
                      f"B{pct_rgb(rgb[2]):>5.1f}") if rgb else " " * 21
                dim = "None" if r["dim"] is None else str(r["dim"])
                out.append(f"   {g:<6} fx{ini}-{fin:<3} DIM {dim:>5}  {rp}  "
                           f"{(r['color'] or '-'):<14} {r['accion']}"
                           f"{'  eff' + str(r['efecto']) if r['efecto'] else ''}"
                           f"{'  MULTICOLOR' if r['multicolor'] else ''}")
            out.append(f"   celdas PDF:")
            for g in COLS_PDF:
                out.append(f"      {g:<3}: {fila['grupos'][g]['bruto']!r}")
            if fila["avisos"]:
                for a in fila["avisos"]:
                    out.append(f"      ! {a}")
            out.append("")
        Path(f"data/_scene{n}.txt").write_text("\n".join(out),
                                               encoding="utf-8")
        print(f"detalle escrito en data/_scene{n}.txt")