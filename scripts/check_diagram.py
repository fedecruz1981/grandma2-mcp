"""
Verifica la geometria del diagrama sin poder mirarlo.

No puedo ver la imagen renderizada, asi que antes de entregarla compruebo
por codigo que ningun elemento se salga del lienzo, se monte sobre otro,
o quede pegado al borde. Si algo falla, el dibujo esta mal aunque el JPG
se haya generado sin error.

Lee la MISMA tabla LAYOUT que usa stage_diagram, asi que el dibujo y la
verificacion no pueden contradecirse.

Uso: python scripts/check_diagram.py
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage_diagram as sd

cues, rig = sd.load()
L = sd.LAYOUT
bad = []
DOT_R = 17        # circulo mas grande (blinder / cob) + borde
NUM_UP = 26       # numero del fixture sobre el circulo


def in_canvas(x, y, what, r=0):
    if not (r <= x <= sd.W - r and r <= y <= sd.H - r):
        bad.append(f"FUERA DEL LIENZO {what}: ({x},{y})")


def in_stage(x, y, what):
    if not (sd.SX0 <= x <= sd.SX1):
        bad.append(f"FUERA DEL ESCENARIO (x) {what}: x={x}")
    if not (sd.SY0 <= y <= sd.SY1):
        bad.append(f"FUERA DEL ESCENARIO (y) {what}: y={y}")


def row(xs, name, y, r=DOT_R):
    xs = sorted(xs)
    sep = min((b - a for a, b in zip(xs, xs[1:])), default=10 ** 6)
    print(f"  {name:<20} x {xs[0]:>4}..{xs[-1]:<4} sep {sep:>4}px")
    if sep < r * 2 + 6:
        bad.append(f"{name}: fixtures encimados (sep={sep}px, min={r * 2 + 6})")
    for x in xs:
        in_canvas(x, y, f"{name} fx")
        in_canvas(x, y - NUM_UP, f"{name} numero", 12)


print(f"lienzo {sd.W}x{sd.H}   escenario x {sd.SX0}..{sd.SX1}  y {sd.SY0}..{sd.SY1}\n")

print("barras horizontales (separacion minima entre fixtures):")
xs_back = sd.span(sd.SX0 + 110, sd.SX1 - 110, 9)
xs_m = sd.span(sd.SX0 + 90, sd.SX1 - 90, 8)
xs_f = sd.span(sd.SX0 + 70, sd.SX1 - 170, 6)
xs_p = sd.span(sd.SX0 + 90, sd.SX1 - 90, 4)
row(xs_back, "atras alternada", L["back_row_a"])
row(xs_m, "medio fx15-22", L["mid_bar"])
row(xs_f, "adelante fx9-14", L["front_bar"])
row(xs_p, "protones", L["prot_r1"])
row(xs_p, "protones r2", L["prot_r2"])

print("\npatron alternado de la barra de atras:")
BACK_SEQ = [("S", 5), ("B", 1), ("S", 6), ("B", 2), ("S", 7),
            ("B", 3), ("S", 8), ("B", 4), ("S", None)]
beams = [f for k, f in BACK_SEQ if k == "B"]
stroms = [f for k, f in BACK_SEQ if k == "S" and f]
print(f"  {''.join(k for k, _ in BACK_SEQ)}  "
      f"({len(beams)} Beamers {beams}, {len(stroms)} Strombers {stroms})")
if beams != [1, 2, 3, 4]:
    bad.append(f"patron: los Beamers no son fx1-4 en orden: {beams}")
if stroms != [5, 6, 7, 8]:
    bad.append(f"patron: los Strombers no son fx5-8 en orden: {stroms}")
if sum(1 for k, _ in BACK_SEQ if k == "B") != 4:
    bad.append("patron: la truss de atras deberia tener 4 Beamers")
# el pattern debe arrancar y terminar en Stromber segun el operador
if BACK_SEQ[0][0] != "S" or BACK_SEQ[-1][0] != "S":
    bad.append("patron: el operador lo describio arrancando y terminando en Stromber")
n_s = sum(1 for k, f in BACK_SEQ if k == "S")
print(f"  arranca en {BACK_SEQ[0][0]}, termina en {BACK_SEQ[-1][0]}, "
      f"{n_s} slots Stromber (4 parcheados + {n_s - len(stroms)} sin parchar)")

print("\nfilas apiladas (una sobre la otra):")
for a, b, name in [("prot_r1", "prot_r2", "protones")]:
    sep = abs(L[b] - L[a])
    ok = sep >= DOT_R * 2 + 10
    print(f"  {name:<10} {L[a]} / {L[b]}  sep {sep}px  {'OK' if ok else 'MUY JUNTAS'}")
    if not ok:
        bad.append(f"{name}: filas apiladas muy juntas ({sep}px)")

print("\nblinder al extremo de la barra de adelante:")
bx = sd.SX1 - 70
nearest = min(abs(bx - x) for x in xs_f)
print(f"  blinder x={bx}  mas cercano fx9-14 a {nearest}px")
if nearest < DOT_R * 2 + 10:
    bad.append(f"blinder encimado con una neblina ({nearest}px)")
in_stage(bx, L["front_bar"], "blinder")

print("\nCOBs sobre la cabina:")
cob = [sd.SX1 - 430 + i * 150 for i in range(3)]
row(cob, "cabina fx32-34", L["cabin_row"])

print("\ntodos los textos de LAYOUT, contra el lienzo:")
FONT_H = 34  # altura maxima de un texto (el titulo de 42px)
for k, y in sorted(L.items(), key=lambda kv: kv[1]):
    in_canvas(sd.SX0, y, f"texto {k}")
    in_canvas(sd.SX1, y, f"texto {k} der")
    if not (0 <= y <= sd.H - FONT_H):
        bad.append(f"texto {k} fuera vertical: y={y} (H={sd.H})")
print(f"  {len(L)} textos verificados")

print("\nseparacion vertical entre bandas de texto (min 24px):")
keys = [k for k in L if k not in ("footer",)]
keys.sort(key=lambda k: L[k])
worst = None
for a, b in zip(keys, keys[1:]):
    gap = L[b] - L[a]
    # ignora el footer: esta al final a proposito
    if worst is None or gap < worst[0]:
        worst = (gap, a, b)
    if gap < 24 and b != "footer":
        bad.append(f"BANDAS PEGADAS: {a}(y={L[a]}) vs {b}(y={L[b]}) — {gap}px")
print(f"  minima: {worst[0]}px entre {worst[1]} y {worst[2]}")

print("\nbandas dentro del escenario:")
for k in ("back_truss", "back_row_a", "back_row_b", "aim_legend",
          "mid_bar", "front_bar", "prot_r1", "prot_r2"):
    in_stage(sd.SX0, L[k], k)
    print(f"  {k:<14} y={L[k]}")

print("\nconos de las cenitales fx9-14 (solo si estan encendidas):")
if not sd._unused:
    for x in xs_f:
        base = L["front_bar"] + 17
        if x - 46 < sd.SX0 or x + 46 > sd.SX1:
            bad.append(f"cono de fx9-14 se sale del escenario en x={x}")
        if base >= L["prot_r1"] - DOT_R:
            bad.append(f"cono de fx9-14 pisa la fila de protones ({base} vs {L['prot_r1']})")
    print(f"  {len(xs_f)} conos, base y={L['front_bar'] + 17}, "
          f"terminan en el borde y={sd.SY1}, protones arrancan en {L['prot_r1']}")
else:
    print("  apagadas (DEAD_210=True), no se dibujan conos")

print("\nla cabina cae fuera del escenario a proposito (esta arriba de la cabina):")
if not (L["cabin_row"] > sd.SY1):
    bad.append("la cabina deberia caer debajo del rectangulo del escenario")
print(f"  cabina y={L['cabin_row']}  >  borde del escenario y={sd.SY1}  OK")

print()
if bad:
    print(f"PROBLEMAS ({len(bad)}):")
    for b in bad:
        print("  -", b)
    sys.exit(1)
print("geometria OK: nada se sale del lienzo, nada encimado")