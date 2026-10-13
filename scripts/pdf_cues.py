"""
Parsea el Cue Sheet del PDF a JSON estructurado, usando la deteccion de
tablas de PyMuPDF (find_tables).

Tres cosas que costaron y quedaron resueltas:

1. Las escenas arrancan a MITAD de pagina, asi que no alcanza con saber la
   pagina: hace falta la coordenada Y de cada fila (table.rows[i].bbox) y
   compararla contra la Y del titulo de escena.

2. Los titulos de escena ocupan mas de una linea ("ESCENA 6 - SI SOLAMENTE
   LO QUERES, MIRA TODO LO / QUE PODES"), asi que hay que juntar las lineas
   siguientes hasta topar con el encabezado de la tabla ("Cue").

3. Una expresion regular del tipo ESCENA (\\d+) - (.*) se come la tabla
   entera: las clases de caracteres tipo [^x] SI matchean el salto de linea.
   Por eso aca no hay regex, solo palabras con coordenada.

Salida: data/pdf_cues.json
  {"Q1": {"scene": "...", "page": 1, "momento": "...",
          "BF": "...", "BM": "...", "BT": "...", "CM": "...", "humo": "..."}}
"""
import json
import re
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
PDF = Path.home() / "Downloads" / "Cues_Luces_Inti_y_Luna.pdf"
OUT = HERE.parent / "data" / "pdf_cues.json"
NOTES_OUT = HERE.parent / "data" / "pdf_notas.md"

Q_RE = re.compile(r"^Q\s*(\d+)$", re.I)
COLS = ["cue", "momento", "BF", "BM", "BT", "CM", "humo"]


def clean(cell):
    if cell is None:
        return ""
    return re.sub(r"\s+", " ", cell.replace("\n", " ")).strip()


def lines_of(words, tol=3.5):
    """Agrupa palabras en lineas de lectura, tolerando el offset de los acentos.

    PyMuPDF saca el texto acentuado como un run separado con ~2pt de
    diferencia de Y respecto del resto de la linea. Ordenando por Y exacto,
    el 'MAS' de "TODO EN GRIS ES MAS DIVERTIDO" queda ANTES que "ESCENA" y
    el titulo sale mutilado. Por eso agrupo por lineas con tolerancia y
    ordeno dentro de cada linea por X.

    Devuelve [[palabra, ...], ...] en orden de lectura.
    """
    ws = sorted(words, key=lambda w: w[1])
    out, cur, last = [], [], None
    for w in ws:
        if last is not None and abs(w[1] - last) > tol:
            out.append(sorted(cur, key=lambda w: w[0]))
            cur = []
        cur.append(w)
        last = w[1]
    if cur:
        out.append(sorted(cur, key=lambda w: w[0]))
    return out


def find_scenes(page):
    """[(y, num, nombre)] de los titulos 'ESCENA N - TITULO' de la pagina.

    El titulo puede ocupar varias lineas ("ESCENA 6 - SI SOLAMENTE LO
    QUERES, MIRA TODO LO / QUE PODES"), asi que sigo|Juniendo lineas hasta
    topar con el encabezado de tabla ("Cue") o con un salto vertical grande.
    """
    lines = lines_of(page.get_text("words"))
    out = []
    for idx, ln in enumerate(lines):
        if not ln or ln[0][4] != "ESCENA":
            continue
        toks = [w[4] for w in ln]
        prev_y = ln[0][1]
        for nxt in lines[idx + 1:]:
            ntok = [w[4] for w in nxt]
            # el encabezado de la tabla corta el titulo
            if "Cue" in ntok or "Momento" in ntok:
                break
            if nxt[0][1] - prev_y > 26:
                break
            toks += ntok
            prev_y = nxt[0][1]
        m = re.match(r"^(\d+)\s*[—–-]?\s*(.*)$", " ".join(toks[1:]))
        if m:
            out.append((ln[0][1], int(m.group(1)), m.group(2).strip(" *")))
    return out


def scene_at(scenes, y):
    """Ultima escena cuyo titulo esta por encima de la coordenada y."""
    chosen = None
    for sy, num, name in scenes:
        if sy < y:
            chosen = (num, name)
    return chosen


def parse_notes(doc):
    """Saca el bloque 'Notas de operacion' del final del PDF."""
    text = "\n".join(doc[i].get_text("text") for i in range(doc.page_count))
    m = re.search(r"Notas de operaci[oó]n(.*)", text, re.S)
    if not m:
        return ""
    body = m.group(1)
    # cortar cuando aparece algo que ya no es nota
    body = re.split(r"\n\s*\n\s*\n", body)[0]
    paras = [" ".join(p.split()) for p in body.split("\n\n") if p.strip()]
    return "\n\n".join(paras).strip()


def parse():
    doc = pymupdf.open(PDF)
    cues = {}
    notes = parse_notes(doc)
    stats = {"tablas": 0, "filas": 0, "cues": 0, "continuacion": 0,
             "duplicados": [], "huerfanas": []}
    last_q = None
    global_scene = (0, "")

    for pno in range(doc.page_count):
        page = doc[pno]
        scenes = find_scenes(page)
        if scenes:
            global_scene = (scenes[0][1], scenes[0][2])

        for tb in page.find_tables().tables:
            stats["tablas"] += 1
            rows = tb.extract()
            if not rows:
                continue
            ncol = len(rows[0])
            for i, row in enumerate(rows[1:]):
                if i >= len(tb.rows):
                    break
                stats["filas"] += 1
                bbox = tb.rows[i + 1].bbox
                ymid = (bbox[1] + bbox[3]) / 2
                cue_cell = clean(row[0]) if row else ""
                m = Q_RE.match(cue_cell)

                # escena vigente para esta fila
                sc = scene_at(scenes, ymid)
                if sc:
                    cur = sc
                else:
                    cur = global_scene

                if m:
                    last_q = f"Q{int(m.group(1))}"
                    if last_q in cues:
                        stats["duplicados"].append((last_q, pno + 1))
                    cues[last_q] = {
                        "scene": f"ESCENA {cur[0]}"
                                 + (f" - {cur[1]}" if cur[1] else ""),
                        "page": pno + 1,
                    }
                    for j in range(1, ncol):
                        cues[last_q][COLS[j]] = clean(row[j]) if j < len(row) else ""
                    stats["cues"] += 1
                elif last_q and cue_cell == "":
                    # continuacion de una tabla que empezo en la pagina anterior
                    stats["continuacion"] += 1
                    for j in range(1, ncol):
                        extra = clean(row[j]) if j < len(row) else ""
                        if extra:
                            k = COLS[j] if j < len(COLS) else f"col{j}"
                            cues[last_q][k] = (
                                f"{cues[last_q].get(k, '')} {extra}").strip()
                else:
                    stats["huerfanas"].append((pno + 1, cue_cell[:40]))

    doc.close()
    return cues, stats, notes


if __name__ == "__main__":
    cues, stats, notes = parse()
    OUT.write_text(json.dumps(cues, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    print(f"{len(cues)} cues -> {OUT}")
    if notes:
        NOTES_OUT.write_text("# Notas de operacion (PDF original)\n\n"
                             + notes + "\n", encoding="utf-8")
        print(f"notas -> {NOTES_OUT}")
    print(f"\ntablas:{stats['tablas']} filas:{stats['filas']} "
          f"cues:{stats['cues']} continuaciones:{stats['continuacion']}")
    if stats["duplicados"]:
        print(f"DUPLICADOS: {stats['duplicados']}")
    if stats["huerfanas"]:
        print(f"huerfanas: {stats['huerfanas'][:5]}")

    nums = sorted(int(q[1:]) for q in cues)
    faltan = [n for n in range(1, max(nums) + 1) if n not in nums]
    print(f"rango Q{min(nums)}..Q{max(nums)}  faltantes: {faltan or 'ninguno'}")

    print("\nescenas:")
    for s in dict.fromkeys(c["scene"] for c in cues.values()):
        qs = [k for k in sorted(cues, key=lambda x: int(x[1:]))
              if cues[k]["scene"] == s]
        print(f"  {s}\n      {qs[0]}..{qs[-1]}  ({len(qs)} cues)")