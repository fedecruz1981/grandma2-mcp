"""
Diagrama de escenario -> JPG, desde data/cues.json + data/rig.json.

LAYOUT (confirmado con el operador, de contra a frente):

  barra de atras    fx1-4   Beamer 250 Mini CCT   4 roboticas, 15ch
                    fx5-8   Stromber CCT          4, 15ch, contraluz
  barra del medio   fx15-22 Nebula Max 162 CCT    8, 5ch
  barra de adelante fx9-14  Nebula Flat 210 CCT   6, 8ch   (en desuso)
                    fx31    Blinder               1, 9ch, mira al publico
  a piso            fx23-30 Protone LED          8, 2ch, dos filas de 4
  sobre la cabina   fx32-34 Par COB II           3, 2ch, blancos calidos

Los angulos pan/tilt de fx1-4 salen de los 153 cues exportados: son los
unicos 4 fixtures moviles del rig, asi que su punteria real es legible.
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data" / "cues.json"
RIG = HERE.parent / "data" / "rig.json"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "escenario.jpg"

W, H = 2000, 1400
BG = (18, 20, 26)
INK = (228, 232, 240)
DIM = (122, 130, 148)
GRID = (38, 42, 52)
STAGE = (38, 44, 58)

# paleta por tipo
C_BEAM = (255, 176, 46)
C_STR = (232, 106, 96)
C_MID = (168, 140, 255)
C_FRONT = (120, 200, 255)
C_BLIND = (220, 120, 200)
C_PROT = (120, 220, 170)
C_COB = (255, 210, 120)

# Lienzo del escenario
SX0, SX1 = 300, 1700
SY0, SY1 = 250, 1120

# LAYOUT: fuente unica de verdad para las coordenadas verticales.
# stage_diagram dibuja desde aca y check_diagram verifica la misma tabla,
# para que no puedan contradecirse.
#
# Por cada barra:  title -> nums (numero del fixture) -> dots -> label
#                  |<-100      |<-41          |0      |+26
LABEL_UP = 100   # separacion del titulo de banda hacia arriba
NUM_UP = 41      # numero del fixture, relativo al circulo (r=15)
LABEL_DOWN = 26  # texto descriptivo, debajo de la barra

LAYOUT = {
    "title": 40,
    "subtitle": 96,

    "back_title": 190,
    "back_truss": 250,
    "back_row_a": 320,       # fila unica alternada fx1-8 (+ 1 hueco)
    "back_row_b": 352,       # dos lineas de texto descriptivo
    "back_row_c": 376,

    "aim_legend": 496,
    "aim_pan": 528,
    "aim_tilt": 558,

    "mid_title": 620,
    "mid_bar": 700,          # fx15-22
    "mid_label": 726,

    "front_title": 770,
    "front_bar": 850,        # fx9-14 + fx31
    "front_label": 876,

    "prot_title": 908,
    "prot_r1": 968,          # fx23-26
    "prot_r2": 1054,         # fx27-30

    "cabin_title": 1150,
    "cabin_row": 1222,       # fx32-34
    "cabin_label": 1270,

    "footer": 1312,
}

# fx9-14 (Nebula Flat 210) son CENITALES: colgadas adelante del escenario,
# mirando al piso. El operador dijo que no se van a usar, asi que se dibujan
# apagadas. Si es al reves, ponelo en False.
DEAD_210 = True
_unused = set(range(9, 15)) if DEAD_210 else set()

# alias para el checker
TRUSS_BACK = LAYOUT["back_truss"]
ROW_A, ROW_B = LAYOUT["back_row_a"], LAYOUT["back_row_b"]
AIM_Y = LAYOUT["aim_legend"]
BAR_MID = LAYOUT["mid_bar"]
BAR_FRONT = LAYOUT["front_bar"]
PROT_R1, PROT_R2 = LAYOUT["prot_r1"], LAYOUT["prot_r2"]
CABINA_Y = LAYOUT["cabin_row"]
H = LAYOUT["footer"] + 90


def font(sz, bold=False):
    for n in ("segoeuib.ttf" if bold else "segoeui.ttf",
              "arialbd.ttf" if bold else "arial.ttf"):
        try:
            return ImageFont.truetype(n, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def span(x0, x1, n):
    step = (x1 - x0) / (n - 1) if n > 1 else 0
    return [int(x0 + i * step) for i in range(n)]


def load():
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    cues = {}
    for k, v in raw.items():
        for c in v["cues"]:
            c["fixtures"] = {int(f): a for f, a in c["fixtures"].items()}
        cues[int(k)] = v
    return cues, json.loads(RIG.read_text(encoding="utf-8"))


def mean_aim(cues, fx):
    ps, ts = [], []
    for d in cues.values():
        for c in d["cues"]:
            a = c["fixtures"].get(fx)
            if not a:
                continue
            pv, tv = a.get("PAN", {}), a.get("TILT", {})
            if pv.get("value") not in (None, ""):
                ps.append(float(pv["value"]))
            if tv.get("value") not in (None, ""):
                ts.append(float(tv["value"]))
    return (sum(ps) / len(ps) if ps else None,
            sum(ts) / len(ts) if ts else None)


def fx_dot(d, x, y, color, fid, r=15, dead=False):
    """Circulo de fixture con su numero encima."""
    fill = tuple(int(c * 0.45 + BG[i] * 0.55) for i, c in enumerate(color)) if dead else color
    d.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=BG, width=3)
    if dead:
        d.ellipse([x - r, y - r, x + r, y + r], outline=DIM, width=2)
    d.text((x - r, y - r - 11), str(fid), font=font(18, True),
           fill=DIM if dead else INK)


def build():
    cues, rig = load()
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # ---------- escenario ----------
    d.rounded_rectangle([SX0, SY0, SX1, SY1], 26, fill=STAGE, outline=GRID, width=3)
    for i in range(1, 7):
        yy = SY0 + (SY1 - SY0) * i / 7
        d.line([(SX0, yy), (SX1, yy)], fill=GRID, width=1)

    # ---------- titulo ----------
    L = LAYOUT
    d.text((SX0, L["title"]), "ESCENARIO  ·  cct obra matias 2026",
           font=font(42, True), fill=INK)
    d.text((SX0, L["subtitle"]), "34 fixtures  ·  155 secuencias / 153 cues  ·  "
                                 "grandMA2 3.9.60.82  ·  todos en Layer 4",
           font=font(20), fill=DIM)

    # ---------- orientacion ----------
    d.text((1780, 60), "CONTRA", font=font(22, True), fill=(140, 148, 168))
    d.text((1780, 86), "fondo del escenario", font=font(16), fill=DIM)
    d.text((1780, 1090), "PUBLICO", font=font(22, True), fill=(140, 148, 168))
    d.text((1780, 1116), "frente de sala", font=font(16), fill=DIM)
    d.line([(1830, 130), (1830, 1080)], fill=GRID, width=2)
    d.polygon([(1830, 1092), (1820, 1072), (1840, 1072)], fill=(140, 148, 168))

    # ---------- BARRA DE ATRAS ----------
    d.line([(SX0, L["back_truss"]), (SX1, L["back_truss"])],
           fill=(120, 128, 145), width=5)
    d.text((SX0, L["back_title"]), "BARRA DE ATRAS", font=font(26, True), fill=C_BEAM)

    # Fila unica alternada. El operador la describio como S-B-S-B-S(...)
    # arrancando y terminando en Stromber. El patch tiene 4 Beamers y
    # 4 Strombers, asi que el patron S-B-S-B-S-B-S-B-S deja UN Stromber
    # sin parchar en el extremo derecho. Se dibuja como hueco.
    xs_back = span(SX0 + 110, SX1 - 110, 9)
    back_seq = [("S", 5), ("B", 1), ("S", 6), ("B", 2), ("S", 7),
                ("B", 3), ("S", 8), ("B", 4), ("S", None)]
    xs_beam = []
    for x, (kind, fid) in zip(xs_back, back_seq):
        d.line([(x, L["back_truss"]), (x, L["back_row_a"])],
               fill=(92, 100, 118), width=2)
        if kind == "B":
            xs_beam.append((x, fid))
            fx_dot(d, x, L["back_row_a"], C_BEAM, fid)
        elif fid:
            fx_dot(d, x, L["back_row_a"], C_STR, fid)
        else:
            # Stromber que el operador recuerda pero no esta parcheado
            d.ellipse([x - 15, L["back_row_a"] - 15, x + 15, L["back_row_a"] + 15],
                      outline=C_STR, width=2)
            d.text((x - 22, L["back_row_a"] - 26), "?", font=font(18, True), fill=C_STR)

    d.text((SX0, L["back_row_b"]),
           "fila alternada   fx1-4 Beamer 250 Mini CCT (roboticas, 15ch)  ·  "
           "fx5-8 Stromber CCT (contraluz, 15ch)", font=font(17), fill=DIM)
    d.text((SX0, L["back_row_c"]),
           "el '?' es un Stromber mas que el operador recuerda en la truss, "
           "pero no hay ninguno parcheado", font=font(16), fill=C_STR)
    xs_b = [x for x, _ in xs_beam]

    # ---------- punteria real de las roboticas ----------
    d.text((SX0, L["aim_legend"]),
           "punteria real grabada en los cues (promedio de los 153 cues)",
           font=font(18), fill=DIM)
    for x, fid in xs_beam:
        pan, tilt = mean_aim(cues, fid)
        if pan is None:
            continue
        ang = math.radians(min(max(pan, 0), 180))
        ex = x + math.cos(ang) * 95
        ey = L["aim_pan"] + math.sin(ang) * 95 * 0.5
        d.line([(x, L["aim_legend"] + 18), (ex, ey)], fill=(255, 205, 110), width=3)
        d.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill=(255, 205, 110))
        d.text((x - 44, L["aim_pan"]), f"pan {pan:.0f}°",
               font=font(15), fill=(255, 205, 110))
        d.text((x - 42, L["aim_tilt"]), f"tilt {tilt:.0f}°",
               font=font(15), fill=(255, 205, 110))

    # ---------- BARRA DEL MEDIO ----------
    d.line([(SX0, L["mid_bar"]), (SX1, L["mid_bar"])], fill=(120, 128, 145), width=4)
    d.text((SX0, L["mid_title"]), "BARRA DEL MEDIO", font=font(26, True), fill=C_MID)
    xs_m = span(SX0 + 90, SX1 - 90, 8)
    for x, fid in zip(xs_m, range(15, 23)):
        fx_dot(d, x, L["mid_bar"], C_MID, fid)
    d.text((SX0, L["mid_label"]), "fx15-22   Nebula Max 162 CCT   8 · 5ch",
           font=font(17), fill=C_MID)

    # ---------- BARRA DE ADELANTE ----------
    d.line([(SX0, L["front_bar"]), (SX1, L["front_bar"])],
           fill=(120, 128, 145), width=4)
    d.text((SX0, L["front_title"]), "BARRA DE ADELANTE", font=font(26, True), fill=C_FRONT)
    xs_f = span(SX0 + 70, SX1 - 170, 6)
    # conos de luz hacia el piso: son cenitales, apuntan abajo
    for x, fid in zip(xs_f, range(9, 15)):
        if not _unused:
            d.polygon([(x - 13, L["front_bar"] + 17),
                       (x + 13, L["front_bar"] + 17),
                       (x + 46, sd.SY1), (x - 46, sd.SY1)],
                      fill=(26, 40, 54))
    for x, fid in zip(xs_f, range(9, 15)):
        fx_dot(d, x, L["front_bar"], C_FRONT, fid, dead=True)
    d.text((SX0, L["front_label"]),
           "fx9-14   Nebula Flat 210 CCT   6 · 8ch   — cenitales, miran al piso",
           font=font(17), fill=DIM if DEAD_210 else C_FRONT)
    fx_dot(d, SX1 - 70, L["front_bar"], C_BLIND, 31, r=17)
    d.text((SX1 - 300, L["front_label"]), "mira al publico",
           font=font(16), fill=C_BLIND)

    # ---------- PROTONES A PISO ----------
    d.text((SX0, L["prot_title"]), "PROTONES A PISO", font=font(26, True), fill=C_PROT)
    xs_p = span(SX0 + 90, SX1 - 90, 4)
    for x, fid in zip(xs_p, [23, 24, 25, 26]):
        fx_dot(d, x, L["prot_r1"], C_PROT, fid, r=14)
    for x, fid in zip(xs_p, [27, 28, 29, 30]):
        fx_dot(d, x, L["prot_r2"], C_PROT, fid, r=14)
    d.text((SX0, L["prot_r1"] + LABEL_DOWN), "fila de adelante   fx23-26",
           font=font(16), fill=C_PROT)
    d.text((SX0, L["prot_r2"] + LABEL_DOWN), "fila de atras   fx27-30",
           font=font(16), fill=C_PROT)

    # ---------- SOBRE LA CABINA ----------
    d.rounded_rectangle([SX1 - 560, L["cabin_row"] - 36, SX1, L["cabin_row"] + 42], 14,
                        fill=(30, 34, 46), outline=C_COB, width=3)
    d.text((SX1 - 545, L["cabin_title"]), "SOBRE LA CABINA",
           font=font(23, True), fill=C_COB)
    for i, fid in enumerate([32, 33, 34]):
        fx_dot(d, SX1 - 430 + i * 150, L["cabin_row"], C_COB, fid, r=17)
    d.text((SX1 - 545, L["cabin_label"]),
           "fx32-34   Par COB II   3 LED blancos calidos, van de frente",
           font=font(17), fill=C_COB)

    # ---------- pie ----------
    d.text((SX0, L["footer"]),
           "orden de patch = orden fisico dentro de cada bloque.  "
           "fx9-14 esta numerado al reves (sec 132 'izquierda' -> fx13-14)."
           + ("   fx9-14 marcadas apagadas: el operador dijo que no se usan."
              if DEAD_210 else ""),
           font=font(17), fill=DIM)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "JPEG", quality=93)
    print(f"escrito {OUT}  ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    build()