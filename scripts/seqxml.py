r"""
Genera el XML de una secuencia grandMA2 para importar por telnet.

Por que generar XML en vez de mandar `At Effect N` comando por comando: la
consola aplica el effect solo si el fixture lo soporta. Medido con cm_probe.py
y effect_test4/5/6.py:

  - fx1-4  (cabezales)  aceptan COLOR1, SHUTTER, FOCUS, PAN, TILT, GOBO1,
                        PRISMA1, FROST, DIM. NO tienen RGB/CMY/CTC.
  - fx23-30 (Protones)  NO aceptan effects de dimmer/shutter (2/3/6) pero si
                        el arcoiris (7) sobre COLORRGB.
  - fx5-22             aceptan el arcoiris (7) y los de dimmer (1/2).

Escribiendo el XML, el <Effect> queda guardado igual que si lo hubiera hecho el
operador a mano en la consola.

Formato confirmado leyendo exports reales (round-trip identico verificado en
import_test.py): un effect es un <Effect name="NOMBRE N"> DENTRO del <CueData>
del atributo al que aplica, seguido de EffectFlags/Rate/Low/High/Phase/Width.

  1,2,3,4,5  -> DIM      sin flags (la consola los omite porque son default)
  6          -> SHUTTER  sin flags
  7          -> COLORRGB1/2/3  con flags (form_index 12/13/14, fase repartida)
  13,23      -> PAN/TILT con flags (low/high propios)

Uso: lo importa build_sequences.py. No toca red.
"""

# ------------------------------------------------------------------ grupos
GRUPOS = {
    "CM":    (1, 4),     # cabezales Beamer 250 Mini  -> rueda COLOR1
    "BT":    (5, 8),     # Stromber
    "FRONT": (9, 14),    # Nebula Flat 210
    "BM":    (15, 22),   # Nebula Max 162
    "BF":    (23, 30),   # Protones chico
    "COB":   (32, 34),   # Par COB II, sobre la cabina (frontal blanco cálido)
}
CON_RGB = {"BT", "FRONT", "BM", "BF"}     # CM no tiene RGB

# Rueda de color de los cabezales: nombre de color -> COLOR1 (0-100).
# Valores sacados de los presets de color del propio show (scripts/wheel_map.py),
# no inventados: red=5.5 yellow=8 green=13 magenta=15.5 orange=20 blue=24
# pink=29 cyan=32.5 cyan claro=40.5 white=0.
#
# La rueda del Beamer 250 Mini no tiene grises: todo lo que sea gris o blanco
# cae en la posicion 0 (blanco) y lo que da la "oscuridad" es el DIM. Por eso
# los grises del diseno nuevo mapean a 0 a proposito, no por olvido.
#
# Los 5 ultimos (Gris palido, Gris muerto, Indigo, Verde jade, Rosa confeti) son
# del diseno de guion (scripts/generar_diseno_guion.py). "Indigo" no existe en
# la rueda: se usa la posicion de magenta (15.5), que es lo mas violeta que hay.
RUEDA = {
    "Negro":          None,
    "Blanco duro":    0,
    "Blanco frío":    0,
    "Blanco cálido":  0,
    "Cálido neutro":  0,
    "Gris frío":      0,
    "Gris neutro":    0,
    "Gris pálido":    0,     # nuevo: la rueda no tiene grises -> blanco, el DIM hace el resto
    "Gris muerto":    0,     # nuevo
    "Ámbar cálido":   20,
    "Ámbar oscuro":   20,
    "Ámbar tenue":    20,
    "Dorado":         8,
    "Rojo":           5.5,
    "Rojo oscuro":    5.5,
    "Naranja":        20,
    "Rosa":           29,
    "Rosa confeti":   29,     # nuevo
    "Amarillo":       8,
    "Verde":          13,
    "Verde suave":    13,
    "Verde jade":     13,     # nuevo
    "Azul":           24,
    "Azul cielo":     32.5,
    "Azul hielo":     32.5,
    "Celeste":        32.5,
    "Cian":           32.5,
    "Cian claro":     40.5,
    "Morado":         15.5,
    "Indigo":         15.5,   # nuevo: no hay indigo en la rueda, se acerca con magenta
}

# (nombre, tipo) por id del pool de effects.
# tipo: "dim"/"shutter" -> sin flags; "rgb" -> arcoiris; "pt" -> PAN/TILT.
EFECTOS = {
    1:  ("Dimmer Sin",           "dim"),
    2:  ("Dimmer Chase",         "dim"),
    3:  ("Dimmer PWM",           "dim"),
    4:  ("Dimmer Random",        "dim"),
    5:  ("Dimmer Even/Odd",      "dim"),
    6:  ("Shutter PWM",          "shutter"),
    7:  ("RGB Rainbow",          "rgb"),
    13: ("Tilt Sin Pan stomp",   "pt"),
    17: ("P/T Cross",            "pt"),
    22: ("P/T Circle",           "pt"),
    23: ("Tilt Sin Pan stomp",   "pt"),
}

# En los cabezales el "arcoiris"/"barrido de color" no existe (no hay RGB):
# `At Effect 7` sobre COLOR1 es no-op (lo probo pt_capture.py). Se sustituye por
# el barrido de POSICION (P/T Cross), que es lo que se ve como barrido de haz.
CM_EFFECT_SUSTITUTO = {7: 17}

# Sobre que atributo va cada efecto cuando su atributo natural no existe.
#
# El ef6 (Shutter PWM) NO se puede escribir sobre SHUTTER en el grupo BM
# (fx15-22, Nebula Max 162): la consola descarta el CueData entero y el strobo
# se pierde en silencio. Medido con scripts/test_strobe_bm2.py, 4 variantes:
#   SHUTTER valor 0 + ef6   -> no se guarda
#   SHUTTER solo ef6        -> no se guarda
#   SHUTTER valor 100 + ef6 -> no se guarda
#   DIM     valor 100 + ef6 -> SI se guarda (8/8 fixtures)
#   control: SHUTTER + ef6 en FRONT (fx9-14) -> SI se guarda
# O sea que el Nebula Max 162 no tiene un shutter animable. El ef6 va sobre DIM,
# que hace el mismo parpadeo porque el fixture no tiene shutter propio.
SIN_SHUTTER = {"BM": {6}}


def atributo_de_efecto(grupo, efecto):
    """Atributo donde escribir un efecto del pool para este grupo."""
    return "DIM" if efecto in SIN_SHUTTER.get(grupo, ()) else None


def pct(v):
    """0-255 -> 0-100, la escala que guarda la consola."""
    return round(v / 255 * 100, 1)


def lineas_efecto(n, attr, idx=0, n_fx=1):
    """Lineas XML del <Effect> para el atributo `attr`, fixture idx de n_fx.

    Las formas estan copiadas de exports reales de la consola
    (scripts/pt_capture.py para el 17, effect_test4/5/6 para el resto):
      7  en COLORRGBn -> form_index 12/13/14, low 100 high 0, fase repartida
      17 en PAN/TILT  -> form_index 22, sub 0/1, low -35 high 35
      13 en PAN/TILT  -> form_index 0/7, low 0/0 y -25/25
      1-6             -> sin EffectFlags (la consola los omite por ser default)
    """
    nombre, tipo = EFECTOS[n]
    out = [f'<Effect name="{nombre} {n}">', "<No>1</No>", f"<No>{n}</No>",
           "</Effect>"]
    flags = None
    absolute = False
    if tipo == "rgb":
        banda = int(attr[-1])                    # COLORRGB1/2/3 -> 1/2/3
        fase = -round(idx * 360 / n_fx) if n_fx > 1 else 0
        flags = (11 + banda, 0, 0.5, 100, 0, fase, 100)
        absolute = True
    elif tipo == "pt":
        # El PHASE reparte el desfase entre fixtures. Con phase 0 en los cuatro
        # cabezales se mueven TODOS al mismo tiempo: eso no se ve como un
        # barrido, se ve como una inclinacion sincronizada. Repartido 0/90/180/270
        # los haces se van cruzando, que es lo que el operador pide para la
        # coreografia de Bigotin ("cabezales barriendo en blanco").
        fase_pt = -round(idx * 360 / n_fx) if n_fx > 1 else 0
        if n == 17:
            flags = (22, 0 if attr == "PAN" else 1, 0.1, -35, 35, fase_pt, 100)
        elif n == 22:
            flags = (22, 0 if attr == "PAN" else 1, 0.1, -35, 35, fase_pt, 100)
        else:                                    # 13, 23
            if attr == "PAN":
                flags = (0, 0, 0.1, 0, 0, 0, 0)
            else:
                flags = (7, 0, 0.1, -25, 25, 0, 100)

    if flags:
        fi, sf, rate, low, high, fase, width = flags
        absat = ' absolute_mode="true"' if absolute else ""
        out += [
            f'<EffectFlags{absat} form_index="{fi}" sub_form_index="{sf}" />',
            f"<EffectRate>{rate}</EffectRate>",
            f"<EffectLow>{low}</EffectLow>", "<EffectLowPreset />",
            f"<EffectHigh>{high}</EffectHigh>", "<EffectHighPreset />",
            f"<EffectPhase>{fase}</EffectPhase>",
            f"<EffectWidth>{width}</EffectWidth>",
        ]
    return out


def cue_data(fx, attr, valor=None, efecto=None, idx=0, n_fx=1, stomp=False,
             sangria="\t" * 5):
    """Bloque <CueData> de un atributo de un fixture.

    `stomp` escribe el flag de STOMP: `<EffectFlags form_index="0"
    sub_form_index="0" />`. Sin el, un valor nuevo se mete DEBAJO del efecto que
    tuviera corriendo ese atributo del cue anterior, y el efecto sigue por
    arriba: el efecto de cambio de color queda "colgado" en los LED. Con el
    flag, el valor pisa el efecto.

    De donde sale el flag: scripts/probar_stomp_en_secuencia.py grabo un cue con
    `Stomp PresetType Thru` y otro sin el, en la misma secuencia y sobre el mismo
    atributo. El unico rastro del stomp en el XML es ese EffectFlags sin
    parametros. (Es el macro 6 "Stomp running Effects" de la consola, que es
    ClearSelection + Stomp PresetType Thru.)
    """
    out = [f'{sangria}<CueData value_multipart_index="0" '
           f'effect_multipart_index="0">',
           f'{sangria}\t<Channel fixture_id="{fx}" attribute_name="{attr}" />']
    if valor is not None:
        out.append(f"{sangria}\t<Value>{valor}</Value>")
    if efecto is not None:
        for ln in lineas_efecto(efecto, attr, idx, n_fx):
            out.append(f"{sangria}\t{ln}")
    elif stomp:
        out.append(f'{sangria}\t<EffectFlags form_index="0" sub_form_index="0" />')
    out.append(f"{sangria}</CueData>")
    return "\n".join(out)


def cue(numero, entradas):
    """
    entradas: lista de (fx, attr, valor, efecto, stomp) donde `efecto` es None
    o (id_del_pool, indice_del_fixture, cantidad_de_fixtures), y `stomp` es el
    flag para pisar el efecto queVenia corriendo.
    Devuelve el bloque <Cue>.
    """
    L = ["\t\t<Cue index=\"%d\">" % numero,
         "\t\t\t<Number number=\"%d\" sub_number=\"0\" />" % numero]
    if entradas:
        L.append("\t\t\t<CueDatas>")
        for entrada in entradas:
            fx, attr, valor, efecto = entrada[:4]
            stomp = entrada[4] if len(entrada) > 4 else False
            if efecto:
                eid, idx, n_fx = efecto
            else:
                eid, idx, n_fx = None, 0, 1
            L.append(cue_data(fx, attr, valor, eid, idx, n_fx, stomp))
        L.append("\t\t\t</CueDatas>")
    L += ["\t\t\t<CuePart index=\"0\">",
          "\t\t\t\t<CuePartPresetTiming>"]
    L += ["\t\t\t\t\t<PresetTiming />"] * 10
    L += ["\t\t\t\t</CuePartPresetTiming>",
          "\t\t\t</CuePart>",
          "\t\t</Cue>"]
    return "\n".join(L)


def secuencia(indice, nombre, cues):
    """
    cues: lista de (numero, entradas).
    Devuelve el XML completo de la secuencia, listo para Import.
    """
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
         ' xmlns="http://schemas.malighting.de/grandma2/xml/MA"'
         ' xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA'
         ' http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd"'
         ' major_vers="3" minor_vers="9" stream_vers="60">',
         f'\t<Info datetime="2026-09-30T00:00:00"'
         f' showfile="fede inti y luna sep 2026" />',
         f'\t<Sequ index="{indice}" name="{nombre}" timecode_slot="255"'
         f' forced_position_mode="0">',
         '\t\t<Cue xsi:nil="true" />']
    for numero, entradas in cues:
        L.append(cue(numero, entradas))
    L += ["\t</Sequ>", "</MA>", ""]
    return "\n".join(L)
