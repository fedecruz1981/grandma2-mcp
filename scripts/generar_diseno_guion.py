r"""
DISEÑO DE LUCES PROPUESTO POR EL AGENTE, leído del guion completo
("Obra teatral INTI Y LUNA: GUERREROS DE LA LUZ", 36 pág.,
 Guion: Francisco Rivera — Dirección: Silvia Gachy Zerda).

No sigue el PDF de cues: sigue el arco dramático del GUION. Los momentos
(Q1-Q53) se conservan porque el guion coincide 1 a 1 con el PDF que ya
tenías grabado, así que no se rompe nada de lo que probaste.

Cómo se decidió cada cosa:

  - Los personajes tienen poder y color propios, y el guion lo dice:
      INTI   = cambia colores / empatía   -> es el arcoíris que se apaga
      LUNA   = calma / congelar          -> blanco cálido, azul hielo
      VALKIRA= tiempo, colores primarios  -> morado + amarillo, destellos
      QOORI  = visión                     -> dorado, luz cenital
      BIGOTIN= sin emociones, gris        -> gris frío, blanco duro, nada de color
  - La escena 6 es el arco central de la obra: GRIS (la tragedia) -> COLOR
    (la redención). Por eso todo Q32-Q48 vive en grises y el color sólo
    aparece a partir de Q49.
  - Las referencias textuales del guion se respetan al pie de la letra:
    "luces amarillas y moradas" (Q17/Q22), "luces blancas y oscuras"
    (Q32), "la luz se apaga lentamente" (Q30), "las luces titilan"
    (Q45/Q46), "las luces giran" (Q49/Q52).
  - NUNCA hay un cue en negro total: los fundidos quedan en gris al 10-15%,
    para que el ojo no se lose y para no romper la regla del operador.

Uso: python scripts\generar_diseno_guion.py
"""
import json
import shutil
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
PLAN = DATA / "plan.json"

# ---------------------------------------------------------------- paleta
# (nombre, RGB 0-255). Los que ya estaban en palette.md se conservan tal
# cual; los marcados NUEVO son de este diseño.
P = {
    # --- blancos y neutros (del PDF)
    "Blanco duro":    (255, 255, 255),
    "Blanco frío":    (214, 232, 255),
    "Blanco cálido":  (255, 232, 196),
    "Cálido neutro":  (255, 240, 220),
    "Gris frío":      (196, 202, 208),
    "Gris neutro":    (190, 190, 190),
    # --- ambar / dorado (del PDF)
    "Ámbar cálido":   (255, 160, 20),
    "Ámbar oscuro":   (180, 90, 10),
    "Dorado":         (255, 190, 60),
    "Ámbar tenue":    (210, 120, 30),
    # --- saturados (del PDF)
    "Rojo":           (255, 0, 0),
    "Naranja":        (255, 120, 0),
    "Rosa":           (255, 60, 130),
    "Amarillo":       (255, 220, 0),
    "Verde":          (0, 255, 60),
    "Azul":           (0, 80, 255),
    "Celeste":        (120, 200, 255),
    "Azul hielo":     (150, 220, 255),
    "Morado":         (130, 0, 255),
    "Cian":           (0, 255, 255),
    # --- NUEVOS de este diseño
    "Gris muerto":    (128, 132, 138),   # gris de "no hay color", el más apagado
    "Gris pálido":    (150, 154, 160),   # gris suave, transición/viaje temporal
    "Indigo":         (70, 40, 160),     # sombra fría de Bigotín (no es negro)
    "Verde jade":     (0, 200, 120),     # verde más saturado, "esperanza"
    "Rosa confeti":   (255, 140, 190),   # rosa suave, fiesta / romance
}

GRUPOS = ("CM", "BT", "FRONT", "BM", "BF", "COB")
COB_ATTRS = {"COLORRGB18": 100, "COLORRGB5": 0}   # = preset CALIDO del Par COB II

# ---------------------------------------------------------------- PAN/TILT
# Posicion de los 4 cabezales (fx1..fx4), en el orden del plan.
#
# Son posiciones ABSOLUTAS, no desplazamientos. El operador pidio "+10 de pan y
# tilt" para que no queden todos apuntando al mismo lado, asi que el PAN esta
# escalonado (10/20/30/40 = "un poco corrida") y el TILT es 10 en los cuatro,
# que es lo que deja los haces hacia abajo.
#
# NO se pudo leer por telnet el rango real del atributo: la consola responde
# "Executing" sin devolver min/max, y no hay ningun PAN/TILT guardado en el
# show del cual sacar la escala (0 valores en las sec 45, 1 y 156). Por eso
# estos numeros arrancan en 10 tal cual los pidio el operador, y hay que
# confirmarlos a ojo en el ensayo.
#
# Si los haces apuntan mal, se corrige SOLO acá y se vuelve a importar:
#   - para moverlos de lado:  cambiar CABEZAS_PT[i][0] (el PAN)
#   - para subirlos o bajarlos: cambiar CABEZAS_PT[i][1] (el TILT)
CABEZAS_PT = [
    (10, 10),    # fx1
    (20, 10),    # fx2
    (30, 10),    # fx3
    (40, 10),    # fx4
]

# La misma posicion, pero con un barrido (ef17) encima: el efecto manda sobre
# el valor estatico, asi que el PAN/TILT queda como referencia del centro.
CABEZAS_PT_BARRIDO = CABEZAS_PT

E1 = "ESCENA 1 - POR VOS"
E2 = "ESCENA 2 - SOY LORD BIGOTIN"
E3 = "ESCENA 3 - LA MIRADA DORADA"
E4 = "ESCENA 4 - REINA GITANA"
E5 = "ESCENA 5 - TODO EN GRIS ES MÁS DIVERTIDO"
E6 = "ESCENA 6 - SI SOLAMENTE LO QUERÉS, MIRA TODO LO QUE PODÉS"

# atajo: ("CM", dim, color, ef)  -> efecto 7 en cabezal se graba como 17
#        ("BT", dim, color, ef)
#        ("COB",)  -> COB 40% Cálido
#        ("alt", [c1, c2], dim)  -> intercalado fixture por fixture (RGB, barras)
#        ("cruz", [c1, c2], dim, ef) -> 1 color de RUEDA por cabezal (COLOR1)
#        ("cabeza", color, dim, ef)  -> cabezales con PAN/TILT fijo, sin barrido
C = {
    "Q1":  (E1, "Apertura: la plaza de Colorilandia, Inti entra y se presenta",
            [("cruz", ["Rojo", "Amarillo", "Verde", "Azul"], 70, 17),
             ("BT", 100, "Celeste", None),
             ("FRONT", 100, "Rojo", 7), ("BM", 100, "Amarillo", 7),
             ("BF", 100, "Verde", 7), ("COB",)],
            "El guion: \"Una plaza de muchos colores... Humo y luces invadian la "
            "escena\". Inti es el arcoiris y este es el unico cue donde esta "
            "COMPLETO: los 4 cabezales en 4 colores distintos de la rueda "
            "(rojo/amarillo/verde/azul) + ef17 para que los haces barran el "
            "arcoiris. Q50 repite este mismo cruce: el final cierra el circulo."),

    "Q2":  (E1, "Inti intenta usar su poder dos veces: falla (PUFF, nada)",
            [("cruz", ["Rojo", "Amarillo", "Blanco duro", "Blanco duro"], 50, 17),
             ("BT", 50, "Cian", 3),
             ("FRONT", 45, "Gris neutro", 3), ("BM", 50, "Gris muerto", 3),
             ("BF", 45, "Azul", 3), ("COB",)],
            "\"Inti intenta lanzar su poder, pero no funciona... NOO, no esta "
            "nada bajo control.\" El arcoiris EMPIEZA A PERDER COLOR de a uno: 2 "
            "cabezales de 4 ya son Blanco duro (no hay color = rueda en 0). Dos "
            "intentos, dos cabezales apagados. La cuenta arranca en 4 y baja."),

    "Q3":  (E1, "\"¿Ven? Casi funciona\" - intenta con el público, las luces parpadean",
            [("CM", 100, "Blanco duro", 6), ("BT", 100, "Blanco duro", 6),
             ("FRONT", 100, "Blanco duro", 4), ("BM", 100, "Blanco duro", 6),
             ("BF", 100, "Blanco duro", 4), ("COB",)],
            "El guion es literal: \"(Las luces del teatro parpadean un poco)\" y "
            "el operador lo pidio explicitamente: AQUI LOS CABEZALES HACEN EL "
            "PARPADEO (ef6). Color muerto (Blanco duro): el arcoiris ya llego a "
            "0 de 4. Es el ultimo cue con color y el primero sin."),

    "Q4":  (E1, "Luna entra y congela a Inti",
            [("CM", 100, "Azul hielo", None),
             ("BT", 100, "Azul hielo", None),
             ("FRONT", 100, "Azul hielo", None), ("BM", 100, "Azul hielo", None),
             ("BF", 100, "Azul hielo", 6), ("COB",)],
            "\"Luna usa sus poderes para congelarlo. Sonido de congelamiento. "
            "Humo. Luces parpadean.\" El operador: EN LOS CONGELADOS VA TODO "
            "AZUL. Antes BM y CM quedaban en Blanco duro y rompian el azul; "
            "ahora los 6 grupos van Azul hielo. Los cabezales SIN ef17 y sin "
            "efecto: el congelamiento tiene que verse fijo, clavado. El "
            "\"parpadean\" del guion queda en BF (ef6). snap: es instantaneo."),

    "Q5":  (E1, "Luna se presenta y lo descongela: \"yo te voy a ayudar\"",
            [("CM", 60, "Cálido neutro", 17), ("BT", 70, "Cálido neutro", None),
             ("FRONT", 60, "Cálido neutro", None), ("BM", 70, "Cálido neutro", None),
             ("BF", 60, "Cálido neutro", None), ("COB",)],
            "Cambio de afectividad: de la tensión al alivio. Luna es dulce y "
            "transmite calma, así que entra el cálido neutro suave. Prepara "
            "la canción de amor."),

    "Q6":  (E2, "Canción \"Por vos\" (entran bailarines)",
            [("cabeza", "Blanco duro", 100, None), ("BT", 70, "Blanco duro", 2),
             ("FRONT", 70, "Blanco duro", 2), ("BM", 70, "Blanco duro", 2),
             ("BF", 70, "Blanco duro", 2)],
            "Escena 2 = SIN COLOR, sólo blancos y grises (decisión del "
            "operador). ESTE ES EL CUE DEL BAILE: el operador lo pidió "
            "apretado. Los 4 cabezales al 100, SIN ef17 y con PAN/TILT fijo "
            "de CABEZAS_PT (TILT 10 = hacia abajo): 4 haces cruzados sobre los "
            "bailarines, quietos. El resto de los grupos baja a 70 para que lo "
            "que brilla sea el haz de los cabezales."),

    "Q7":  (E2, "Fin de la canción, salen bailarines, Inti y Luna quedan solos",
            [("CM", 40, "Gris pálido", 17), ("BT", 50, "Gris pálido", None),
             ("FRONT", 45, "Gris pálido", None), ("BM", 50, "Blanco frío", None),
             ("BF", 45, "Gris pálido", None)],
            "La fiesta se cae y empieza el traslado a Grisolin. Gris pálido, "
            "casi niebla: es un respiro. Los cabezales vuelven al barrido "
            "ef17 (siguen con PAN/TILT de referencia) para no quedarse mudos "
            "en un plano que es todo gris."),

    "Q8":  (E2, "\"Todo se vuelve oscuro\" - salida de Inti y Luna",
            [("CM", 12, "Gris muerto", 17), ("BT", 15, "Gris muerto", None),
             ("FRONT", 12, "Gris muerto", None), ("BM", 15, "Gris muerto", None),
             ("BF", 12, "Gris muerto", None)],
            "El umbral entre dos mundos. El guion pide oscuro, pero se deja un "
            "15% de gris: fundido, no corte al negro. Los cabezales barren ese "
            "15% con ef17; a esa altura el barrido se ve como una sombra que pasa."),

    "Q9":  (E2, "Entra Bigotín (humo + música maléfica)",
            [("CM", 100, "Blanco duro", 17), ("BT", 100, "Blanco duro", 2),
             ("FRONT", 100, "Gris frío", 2), ("BM", 100, "Gris neutro", None),
             ("BF", 100, "Blanco duro", 2)],
            "\"Ingresa por un costado. Humo y música maléfica lo acompañan.\" "
            "La entrada del villano tiene que ser ominosa: blanco duro de "
            "contraluz y sombra gris alrededor. Nada de color: su reino no "
            "tiene colores."),

    "Q10": (E2, "Monólogo inicial / \"achís\" - se presenta como señor de Grisolin",
            [("CM", 60, "Gris neutro", 17), ("BT", 70, "Gris neutro", None),
             ("FRONT", 60, "Gris neutro", None), ("BM", 70, "Gris neutro", None),
             ("BF", 60, "Gris neutro", None)],
            "\"Tantos colores juntos, tanta luz... Me da alergia. ACHIS.\" Su "
            "mundo es aburrido, gris y elegante: un solo plano gris uniforme "
            "para que el monólogo pese. Los cabezales quedan en ef17, que es "
            "movimiento sin color: el gris se mantiene, la vida tambien."),

    "Q11": (E2, "Canción \"Lord Bigotín\" (coreografía del villano)",
            [("CM", 100, "Blanco duro", 17), ("BT", 70, "Blanco frío", 2),
             ("FRONT", 70, "Blanco duro", 2), ("BM", 70, "Blanco duro", 6),
             ("BF", 70, "Blanco duro", 2)],
            "\"Yo cierro el sol, todo brillante pierde valor.\" SEGUNDO CUE DE "
            "BAILE, y el que el operador pidió explícitamente: CABEZALES "
            "BARRIENDO EN BLANCO. Tiene que ser ef17 (P/T Cross) sobre PAN y "
            "TILT, no posición fija: es la coreografía del villano y los haces "
            "lo tienen que recorrer, no quedar clavados. El phase del ef17 va "
            "repartido 0/90/180/270 entre los cuatro cabezales para que los "
            "haces se CRUCEN entre sí (con phase 0 los cuatro se mueven juntos y "
            "eso se ve como una inclinación, no como un barrido). Al 100 y en "
            "blanco duro contra el resto a 70; el ef6 queda en BM para los "
            "golpes de la música."),

    "Q12": (E3, "Inti y Luna se buscan, llega Qoori",
            [("CM", 80, "Dorado", 17), ("alt", ["Cian", "Dorado"], 50),
             ("FRONT", 50, "Dorado", 7), ("alt", ["Cian", "Dorado"], 50),
             ("BF", 40, "Dorado", None), ("COB",)],
            "El título de la escena es LA MIRADA DORADA, así que el dorado "
            "arranca desde el primer cue. En las barras (BT y BM) va el "
            "cian intercalado con dorado fixture por fixture al 50%, que es "
            "lo que pidió el operador."),

    "Q13": (E3, "Inti se pone nervioso, Luna lo congela y lo tranquiliza",
            [("CM", 100, "Azul hielo", None),
             ("BT", 100, "Azul hielo", None),
             ("FRONT", 100, "Azul hielo", None),
             ("BM", 100, "Azul hielo", None),
             ("BF", 100, "Azul hielo", None), ("COB",)],
            "Nerviosismo de Inti que Luna corta CONGELÁNDOLO. El operador fue "
            "claro: en los congelados va TODO azul. Antes este cue mezclaba "
            "Indigo + Cian + Dorado con ef3 y pulsos, y no se leía como un "
            "congelamiento. Ahora los 6 grupos van Azul hielo al 100, sin "
            "efectos: fijo, cristalino, clavado. Excepción consciente: se "
            "rompe el cian/dorado intercalado al 50% de esta escena durante UN "
            "cue, porque el congelamiento tiene que leerse entero."),

    "Q14": (E3, "Qoori explica: si los colores desaparecen, Colorilandia muere",
            [("CM", 100, "Dorado", 17), ("alt", ["Cian", "Dorado"], 50),
             ("FRONT", 60, "Dorado", 7), ("alt", ["Cian", "Dorado"], 50),
             ("BF", 50, "Dorado", 7), ("COB",)],
            "\"Los colores son la energía de Colorilandia.\" Momento de peso: "
            "el dorado sube y el ef17 barre el haz como unaergen que se "
            "revela. Las barras siguen al 50% intercaladas."),

    "Q15": (E3, "Canción \"Tu nombre\" (Parchís) - Inti y Luna se toman de la mano",
            [("CM", 70, "Rosa", 17), ("alt", ["Cian", "Dorado"], 50),
             ("FRONT", 50, "Rosa confeti", 7), ("alt", ["Cian", "Dorado"], 50),
             ("BF", 60, "Rosa confeti", 7), ("COB",)],
            "\"Ambos se miran. Se presuman... quedan agarrados de la mano.\" "
            "Tierno y ligero: rosa en el resto, y las barras conservan el "
            "cian/dorado del operador."),

    "Q16": (E3, "Qoori mira a Grisolin: \"una energía oscura, una caja... BIGOTÍN\"",
            [("CM", 100, "Ámbar oscuro", 17), ("alt", ["Cian", "Dorado"], 50),
             ("FRONT", 50, "Dorado", 6), ("alt", ["Cian", "Dorado"], 50),
             ("BF", 40, "Ámbar oscuro", 6), ("COB",)],
            "\"Una luz cenital cae sobre ella... Sonido de poder.\" Contraste "
            "brutal: el dorado se apaga a ámbar oscuro y entra el strobo ef6 "
            "para el golpe de \"LORD BIGOTÍN\"."),

    "Q17": (E4, "Entra Valkira: \"luces amarillas y moradas\"",
            [("CM", 100, "Dorado", 17), ("BT", 100, "Morado", 2),
             ("FRONT", 100, "Amarillo", 7), ("BM", 100, "Indigo", 2),
             ("BF", 100, "Amarillo", 7), ("COB",)],
            "El guion lo dice textualmente: \"Luces amarillas y moradas "
            "convierten el ambiente en magia y alegría.\" Su vestido es morado "
            "con detalles amarillos, así que morado + amarillo es ella."),

    "Q18": (E4, "Valkira pregunta por los colores primarios: rojo, azul, amarillo",
            [("CM", 70, "Amarillo", 17), ("BT", 70, "Rojo", None),
             ("FRONT", 70, "Amarillo", None), ("BM", 70, "Azul", None),
             ("BF", 70, "Rojo", None), ("COB",)],
            "\"¿Cuáles son los colores primarios? El rojo, el azul... y el "
            "amarillo.\" Guiño: cada grupo toma un primario distinto."),

    "Q19": (E4, "Valkira siente una chispa: \"están perdiendo su brillo\"",
            [("cruz", ["Amarillo", "Blanco duro", "Blanco duro", "Blanco duro"],
              60, 17),
             ("BT", 50, "Morado", 3),
             ("FRONT", 50, "Ámbar tenue", 3), ("BM", 50, "Gris pálido", 3),
             ("BF", 50, "Ámbar tenue", 3), ("COB",)],
            "\"Acabo de sentir una chispa acá... ¿algunos colores están "
            "perdiendo su brillo?\" PRIMER AVISO DE LA PÉRDIDA: en los "
            "cabezales quedan 1 de 4 con color (el primero sigue en Amarillo) "
            "y los otros 3 ya son Blanco duro. El ef17 los barre para que se "
            "lea que el que conserva color es UNO solo."),

    "Q20": (E4, "Canción \"Jugate Ya\" (entran bailarines)",
            [("CM", 100, "Amarillo", 17), ("BT", 100, "Verde jade", 2),
             ("FRONT", 100, "Amarillo", 2), ("BM", 100, "Verde", 2),
             ("BF", 100, "Verde jade", 2), ("COB",)],
            "\"Es tu momento... Vení, vení, vení, jugate ya!\" La canción "
            "motivacional: la luz se enciende, verdes y amarillos en chase "
            "sincronizado porque todos bailan al unísono."),

    "Q21": (E4, "Fin de escena, \"todo se vuelve oscuro\"",
            [("CM", 10, "Gris muerto", 17), ("BT", 12, "Gris muerto", None),
             ("FRONT", 10, "Gris muerto", None), ("BM", 12, "Gris muerto", None),
             ("BF", 10, "Gris muerto", None), ("COB",)],
            "Corte a oscuro entre escenas. 10-12% de gris para que sea un "
            "fundido y no un apagón (regla: nunca negro total). El COB de "
            "cabina sigue al 40% como en el resto de las escenas."),

    "Q22": (E4, "Canción \"Luz de estrella\" (con el público) - clímax de la escena",
            [("CM", 100, "Amarillo", 17), ("BT", 100, "Morado", 7),
             ("FRONT", 100, "Amarillo", 7), ("BM", 100, "Morado", 7),
             ("BF", 100, "Rosa confeti", 2), ("COB",)],
            "\"Luz de estrella, la única, la más bella.\" Clímax de Valkira: "
            "su morado y el amarillo del destello de la estrella, con arcoíris "
            "para el baile con el público."),

    "Q23": (E4, "Valkira termina la canción y se acerca al público",
            [("CM", 70, "Dorado", 17), ("BT", 70, "Morado", None),
             ("FRONT", 70, "Amarillo", None), ("BM", 70, "Morado", None),
             ("BF", 70, "Dorado", None), ("COB",)],
            "Vuelve al diálogo: baja la energía, sin efectos, morado y "
            "dorado. Es conversación, no espectáculo."),

    "Q24": (E5, "Bigotín con la caja: \"no más azul, no más amarillo, no más rojo\"",
            [("cruz", ["Azul", "Amarillo", "Blanco duro", "Blanco duro"], 70, 17),
             ("BT", 70, "Azul", 7),
             ("FRONT", 70, "Amarillo", 7), ("BM", 70, "Rojo", 7),
             ("BF", 70, "Verde", 7), ("COB",)],
            "\"No más AZUL, no más AMARILLO, no más ROJO, no más VERDE. Y sobre "
            "todo no más MORADO.\" Los enumera uno por uno, así que cada grupo "
            "es uno de esos colores con ef7: los ve y los apaga. Y es literal "
            "en los cabezales: 2 de 4 (el 1 y el 2) todavía muestran azul y "
            "amarillo, los otros 2 ya no tienen color. La cuenta va 4→1→2→0."),

    "Q25": (E5, "Valkira percibe que los colores pierden brillo",
            [("cruz", ["Amarillo", "Blanco duro", "Blanco duro", "Blanco duro"],
              50, 17),
             ("BT", 60, "Ámbar tenue", 3),
             ("FRONT", 50, "Gris pálido", 3), ("BM", 60, "Ámbar tenue", 3),
             ("BF", 50, "Gris pálido", 3), ("COB",)],
            "\"Acabo de sentir una chispa acá.\" El calor que se va. En los "
            "cabezales el último con color es el 1, y baja a 50%: el arcoíris "
            "de Q1 se quedó en un solo haz y apagándose. ef17 para que el "
            "haz se mueva mientras le queda color."),

    "Q26": (E5, "Canción \"El ejercicio de la sonrisa\" - Valkira hace sonreír a Inti",
            [("CM", 100, "Amarillo", 17), ("BT", 100, "Naranja", 2),
             ("FRONT", 100, "Amarillo", 2), ("BM", 100, "Dorado", 2),
             ("BF", 100, "Rosa confeti", 7), ("COB",)],
            "\"Abrimos grande nuestra boca... Cuando todos sonreímos, mucho "
            "más fácil es.\" Un oasis de color cálido dentro de la tristeza. "
            "Oasis a propósito: es la última alegría antes de la caída."),

    "Q27": (E5, "\"¿Quieren viajar en el tiempo?\" - Valkira inicia el viaje",
            [("CM", 80, "Blanco duro", 6), ("BT", 80, "Gris pálido", 6),
             ("FRONT", 80, "Gris pálido", 2), ("BM", 80, "Gris pálido", 6),
             ("BF", 80, "Gris pálido", 2), ("COB",)],
            "\"Humo y las luces comienzan a parpadear. Sonido de viaje en el "
            "tiempo.\" Parpadeo de glitch: strobo ef6 en casi todo, gris que "
            "se mueve con ef2. Es la elipsis antes del flashback."),

    "Q28": (E5, "FLASHBACK: Bigotín joven jardinero con Valkira joven",
            [("CM", 100, "Blanco cálido", 17), ("BT", 80, "Ámbar cálido", None),
             ("FRONT", 70, "Ámbar cálido", None), ("BM", 80, "Ámbar tenue", None),
             ("BF", 70, "Ámbar cálido", None), ("COB",)],
            "\"Una roja por aquí, una amarilla por allá... Algún día voy a "
            "llenar de color el planeta.\" El Bigotín bueno. Se mantiene el "
            "código ámbar de los flashbacks que pide el PDF. Sin efectos: "
            "es un recuerdorwarm y estático."),

    "Q29": (E5, "Canción \"Reina Gitana\" - bailan enamorados en el recuerdo",
            [("CM", 100, "Dorado", 17), ("BT", 100, "Dorado", 2),
             ("FRONT", 100, "Ámbar cálido", 2), ("BM", 100, "Dorado", 2),
             ("BF", 100, "Ámbar cálido", 2), ("COB",)],
            "\"Reina gitana y olé... Y voy por ti, bonito.\" La versión más "
            "luminosa y cálida de la obra: dorado de atardecer bouncing."),

    "Q30": (E5, "\"La luz se apaga lentamente\" - vuelven al presente",
            [("CM", 30, "Gris muerto", 17), ("BT", 35, "Gris muerto", None),
             ("FRONT", 30, "Gris muerto", None), ("BM", 35, "Gris muerto", None),
             ("BF", 30, "Gris muerto", None), ("COB",)],
            "El guion dice \"se apaga lentamente\": niveles que caen al 30%, "
            "sin efecto, todo gris. El recuerdo se disipa y volvemos al "
            "presente (que ya es gris)."),

    "Q31": (E5, "Cierre de escena: \"¡POR COLORILANDIA!\" - todos salen",
            [("CM", 15, "Ámbar oscuro", 17), ("BT", 18, "Ámbar oscuro", None),
             ("FRONT", 15, "Ámbar oscuro", None), ("BM", 18, "Ámbar oscuro", None),
             ("BF", 15, "Ámbar oscuro", None), ("COB",)],
            "La última llama de Colorilandia antes de apagarse: un rescoldo "
            "ámbar al 15-18%. No es fiesta todavía, es el preludio de la caída."),

    "Q32": (E6, "Apertura: \"humo y luces blancas y oscuras\", la caja brilla",
            [("CM", 60, "Gris frío", 6), ("BT", 70, "Gris neutro", None),
             ("FRONT", 60, "Gris frío", None), ("BM", 70, "Gris neutro", None),
             ("BF", 60, "Gris frío", None), ("COB",)],
            "\"Humo y luces blancas y oscuras... La máquina brilla.\" Empieza el "
            "arco gris de la escena 6. Opresivo. El brillo metálico de la caja "
            "es el strobo ef6 del cabezal."),

    "Q33": (E6, "Bigotín habla con la caja: \"mi hermosa cajita\"",
            [("CM", 50, "Indigo", 17), ("BT", 60, "Indigo", None),
             ("FRONT", 50, "Indigo", None), ("BM", 60, "Gris muerto", None),
             ("BF", 50, "Indigo", None), ("COB",)],
            "\"Le habla como si fuera su bebé.\" Indigo: ya no es blanco de "
            "Grisolin, es algo más frío y malvado. Un solo plano, sin efectos."),

    "Q34": (E6, "Bigotín enciende la máquina: \"ruido extraño, mucho humo, las luces titilan\"",
            [("CM", 100, "Blanco duro", 6), ("BT", 100, "Gris frío", 6),
             ("FRONT", 100, "Gris frío", 6), ("BM", 100, "Blanco duro", 6),
             ("BF", 100, "Gris frío", 6), ("COB",)],
            "\"Las luces comienzan a titilar. Se prenden y apagan.\" Strobe "
            "masivo: es el mundo entero titilando mientras le drenan el color. "
            "Máxima tensión del arranque."),

    "Q35": (E6, "Colorilandia se vuelve gris - la máquina gana",
            [("CM", 85, "Blanco duro", 17), ("BT", 80, "Gris neutro", None),
             ("FRONT", 70, "Gris neutro", None), ("BM", 80, "Gris neutro", None),
             ("BF", 70, "Gris neutro", None), ("COB",)],
            "\"Donde antes había color, ahora solo hay tristeza.\" CUENTA "
            "LLEGÓ A 0: en los cabezales ya no queda ni un color, los 4 son "
            "Blanco duro. El resto del escenario gris neutro. Los cabezales a "
            "85 (no 70) y con ef17: es el último punto donde se los ve bien, "
            "así que tienen que ser ellos los que barren el blanco que dice "
            "\"ya no hay color\". snap, porque se apaga de golpe."),

    "Q36": (E6, "\"¡BIENVENIDOS A GRISOLIN!\" - remate, Bigotín sale",
            [("CM", 12, "Blanco duro", 17), ("BT", 15, "Gris muerto", None),
             ("FRONT", 12, "Gris muerto", None), ("BM", 15, "Gris muerto", None),
             ("BF", 12, "Gris muerto", None), ("COB",)],
            "El punto más bajo antes de que lleguen los héroes. Muy oscuro "
            "pero no negro: 12-15%, como una noche cerrada. Los cabezales "
            "conservan ef17: esa última sombra que cruza es lo que queda del "
            "arcoíris antes de que empiece a volver (Q46)."),

    "Q37": (E6, "\"¡Llegamos tarde!\" - Inti, Luna y Valkira ven todo gris",
            [("CM", 70, "Blanco frío", 3), ("BT", 80, "Gris frío", 3),
             ("FRONT", 70, "Gris frío", 3), ("BM", 80, "Gris frío", 3),
             ("BF", 70, "Gris frío", 3), ("COB",)],
            "El gris del duelo. Es otro gris que el de Bigotín: más frío, y "
            "late (ef3) como si temblaran al ver su mundo muerto."),

    "Q38": (E6, "Entra Bigotín: \"bienvenidos a Grisolin, mi nuevo reino\"",
            [("CM", 100, "Blanco duro", 17), ("BT", 100, "Blanco duro", 2),
             ("FRONT", 100, "Gris frío", 2), ("BM", 100, "Gris neutro", None),
             ("BF", 100, "Blanco duro", 2), ("COB",)],
            "El villano en su reino, igual que su entrada en Q9: blanco duro "
            "de contraluz y gris alrededor. El público es su espejo."),

    "Q39": (E6, "Inti hace fuerza contra la caja y pide ayuda al público",
            [("CM", 80, "Ámbar tenue", 17), ("BT", 80, "Ámbar tenue", 3),
             ("FRONT", 80, "Ámbar tenue", 3), ("BM", 80, "Ámbar tenue", 3),
             ("BF", 80, "Ámbar tenue", 3), ("COB",)],
            "\"Vamos todos, manden sus energías. Vamos con más fuerza.\" El "
            "esfuerzo desesperado: ámbar que late (ef3) como el calor de la "
            "fuerza que le ponen."),

    "Q40": (E6, "Bigotín se burla y aparta la caja: \"la caja ya no sirve\"",
            [("CM", 40, "Gris neutro", 3), ("BT", 50, "Gris neutro", 3),
             ("FRONT", 40, "Gris neutro", 3), ("BM", 50, "Gris frío", 3),
             ("BF", 40, "Gris neutro", 3), ("COB",)],
            "El esfuerzo se apaga y todo vuelve al gris. El ef3 es una ironía: "
            "la luz titila y se rinde, como la esperanza de Inti."),

    "Q41": (E6, "\"La solución está en el pasado\" - segundo viaje en el tiempo",
            [("CM", 80, "Blanco duro", 6), ("BT", 80, "Ámbar tenue", 6),
             ("FRONT", 80, "Ámbar tenue", 2), ("BM", 80, "Ámbar tenue", 6),
             ("BF", 80, "Ámbar tenue", 2), ("COB",)],
            "El glitch temporal otra vez (ef6), pero con un ámbar tenue "
            "asomando: esta vez el viaje trae la verdad."),

    "Q42": (E6, "FLASHBACK: Bigotín joven con la caja de flores",
            [("CM", 100, "Blanco cálido", 17), ("BT", 90, "Dorado", None),
             ("FRONT", 80, "Dorado", None), ("BM", 90, "Dorado", None),
             ("BF", 80, "Ámbar cálido", None), ("COB",)],
            "\"Hoy le voy a regalar las flores... Le va a encantar. Yo sé.\" "
            "Todavía tiene toda la intención buena: dorado más brillante que "
            "el otro flashback, porque aún tiene esperanza."),

    "Q43": (E6, "Bigotín arranca las flores y se convierte en Lord Bigotín",
            [("CM", 50, "Indigo", 6), ("BT", 60, "Indigo", 3),
             ("FRONT", 50, "Gris muerto", 3), ("BM", 60, "Gris muerto", 3),
             ("BF", 50, "Indigo", 3), ("COB",)],
            "\"Los colores no sirven para nada. Los sueños tampoco. AHORA SOY "
            "LORD BIGOTÍN.\" La caída: el dorado muere en indigo y gris. "
            "Strobe ef6 en el cabezal para el golpe de la transformación."),

    "Q44": (E6, "Valkira joven encuentra las flores tiradas y sale triste",
            [("CM", 50, "Gris pálido", 17), ("BT", 60, "Blanco frío", None),
             ("FRONT", 50, "Gris pálido", None), ("BM", 60, "Blanco frío", None),
             ("BF", 50, "Gris pálido", None), ("COB",)],
            "\"¿Y estas flores? Son las del señor bigotudo. (Se pone triste).\" "
            "La otra víctima. Melancolía estática, sin efectos: gris pálido y "
            "blanco frío."),

    "Q45": (E6, "\"Las luces parpadean\" - vuelven todos al presente",
            [("CM", 70, "Gris neutro", 6), ("BT", 80, "Gris neutro", 6),
             ("FRONT", 70, "Gris neutro", 2), ("BM", 80, "Gris neutro", 6),
             ("BF", 70, "Gris neutro", 2), ("COB",)],
            "De vuelta del flashback al presente gris. El parpadeo del viaje "
            "temporal otra vez (ef6). Es el pivote de todo el relato."),

    "Q46": (E6, "\"¡Miren! Parece que están volviendo los colores\"",
            [("cruz", ["Rosa confeti", "Blanco duro", "Blanco duro",
                       "Blanco duro"], 70, 17),
             ("BT", 50, "Gris pálido", 7),
             ("FRONT", 50, "Gris pálido", 7), ("BM", 50, "Gris pálido", 7),
             ("BF", 50, "Gris pálido", 4), ("COB",)],
            "El amague: el guion dice \"Parece que\", así que NO vuelve el "
            "color, asoma UN SOLO haz. Exactamente 1 de los 4 cabezales "
            "(Rosa confeti) y los otros 3 sin color: es el amague, y se ve "
            "porque el público ya aprendió a contar los cabezales con color "
            "en Q1 (4), Q2 (2), Q19 (1), Q24 (2), Q25 (1), Q35 (0). El resto "
            "del escenario sigue en gris con ef7 asomando. BF lleva ef4 "
            "(random) que es el \"titilan\" del texto."),

    "Q47": (E6, "El amague falla: \"¡No! No volvió nada\" - Inti se sienta triste",
            [("CM", 40, "Blanco duro", 17), ("BT", 50, "Gris muerto", 4),
             ("FRONT", 40, "Gris muerto", 4), ("BM", 50, "Gris muerto", 4),
             ("BF", 40, "Gris muerto", 4), ("COB",)],
            "El amague se muere: el único cabezal con color vuelve a Blanco "
            "duro y son 0 de 4 otra vez, como en Q35. El conteo empieza a "
            "subir recién en Q49. ef4 (Dimmer Random) en el resto = parpadeo "
            "irregular, el más frustrante de los tres."),

    "Q48": (E6, "Qoori: \"los colores nacen de la confianza\"",
            [("CM", 80, "Blanco cálido", 17), ("BT", 80, "Cálido neutro", None),
             ("FRONT", 80, "Cálido neutro", None), ("BM", 80, "Cálido neutro", None),
             ("BF", 80, "Cálido neutro", None), ("COB",)],
            "\"La caja nunca fue el problema. Bigotín tampoco... Los colores "
            "nacen de la confianza.\" La verdad revelada es luz: cálido neutro "
            "limpio, sin efectos, alto. La luz como respuesta."),

    "Q49": (E6, "Canción \"Penitas\" - empiezan a volver los colores",
            [("cruz", ["Rosa confeti", "Amarillo", "Blanco duro", "Blanco duro"],
              100, 17),
             ("BT", 80, "Rosa confeti", 7),
             ("FRONT", 80, "Celeste", 7), ("BM", 80, "Verde jade", 7),
             ("BF", 80, "Amarillo", 2), ("COB",)],
            "\"Siente como vuelven sus poderes... le va devolviendo a "
            "Colorilandia sus colores. Las luces comienzan a girar.\" EL "
            "CONTEO VUELVE A SUBIR: 2 de 4 cabezales con color (Rosa confeti y "
            "Amarillo) contra 2 blancos. El resto del escenario con ef7. El "
            "público reconoce el 2 porque es el mismo número de Q2."),

    "Q50": (E6, "Clímax de \"Penitas\" - Colorilandia recuperada, todos bailan",
            [("cruz", ["Rojo", "Amarillo", "Verde", "Azul"], 100, 17),
             ("BT", 100, "Rosa confeti", 7),
             ("FRONT", 100, "Celeste", 7), ("BM", 100, "Verde jade", 7),
             ("BF", 100, "Verde", 7), ("COB",)],
            "\"Colorilandia recuperó sus colores gracias a Luna e Inti.\" "
            "Estalla: arcoíris al 100% en todos los grupos. Saturación máxima. "
            "Y los 4 cabezales vuelven EXACTAMENTE al cruce de Q1 "
            "(rojo/amarillo/verde/azul): el cierre del arco, el público ve "
            "volver el arcoíris con el que abrió la obra."),

    "Q51": (E6, "Diálogo final: \"¡volvemos a intentarlo!\" - la magia está dentro",
            [("CM", 80, "Cálido neutro", 17), ("BT", 90, "Cálido neutro", None),
             ("FRONT", 90, "Cálido neutro", None), ("BM", 90, "Cálido neutro", None),
             ("BF", 90, "Cálido neutro", None), ("COB",)],
            "\"Cuando tienen miedo... ¿se rinden? ¡Volvemos a intentarlo!\" El "
            "mensaje es para el público, así que luz abierta y constante, sin "
            "efectos: que se lea claro."),

    "Q52": (E6, "Canción final \"Corazones al viento\" - las luces giran",
            [("CM", 100, "Blanco duro", 17), ("BT", 100, "Amarillo", 7),
             ("FRONT", 100, "Rosa confeti", 7), ("BM", 100, "Celeste", 7),
             ("BF", 100, "Verde jade", 7), ("COB",)],
            "\"Las luces giran... Para todos una fiesta.\" El gran final: "
            "arcoíris girando en todos los grupos, caben al 100%."),

    "Q53": (E6, "Salida, aplausos, FIN",
            [("CM", 100, "Blanco duro", 17), ("BT", 100, "Amarillo", 7),
             ("FRONT", 100, "Rosa confeti", 7), ("BM", 100, "Celeste", 7),
             ("BF", 100, "Verde", 7), ("COB",)],
            "Curtain call. Se queda en el clímax de color, no vuelve al gris: "
            "la obra termina en la fiesta de Colorilandia recuperada."),
}


def grupo(dim, color, efecto=None, alt=None, acc="cambiar", rueda_alt=None,
          pt=None):
    """Arma un grupo del plan. `color` puede ser None si va `alt` o `rueda_alt`.

    `pt` es la lista de posiciones (pan, tilt) por fixture de los cabezales.
    OJO: es posicion ABSOLUTA, no desplazamiento. Antes de este diseno no habia
    ningun PAN/TILT guardado en el show, asi que las secuencias no manejaban la
    posicion de los cabezales. Los numeros viven en CABEZAS_PT mas abajo.
    """
    d = {
        "accion": acc, "dim": dim, "color": None, "rgb": None,
        "efecto": efecto, "multicolor": efecto == 7,
        "shutter": None, "snap": False, "segundos": None,
        "manual": [], "avisos": [],
    }
    if pt:
        d["pt"] = [list(p) for p in pt]
        d["avisos"].append(
            "posicion PAN/TILT por cabezal: "
            + " / ".join(f"fx{i+1}(p{a},t{b})" for i, (a, b) in enumerate(pt)))
    if rueda_alt:
        # Un color de la rueda COLOR1 por fixture. Es lo UNICO que permite que
        # los 4 cabezales muestren 4 colores distintos: el Beamer 250 Mini no
        # tiene RGB, su color vive en la rueda (COLOR1). Se cicla la lista.
        d["rueda_alt"] = list(rueda_alt)
        d["color"] = rueda_alt[0]
        d["rgb"] = list(P[rueda_alt[0]])
        d["avisos"].append(
            "1 color de rueda por cabezal (COLOR1): " + " / ".join(rueda_alt))
    elif alt:
        d["alternar_rgb"] = [list(P[c]) for c in alt]
        d["color"] = alt[0]
        d["rgb"] = list(P[alt[0]])
        d["avisos"].append(
            "intercalado fixture por fixture: " + " / ".join(alt))
    elif color:
        d["color"] = color
        d["rgb"] = list(P[color])
    d["bruto"] = f"{dim}% {color or ''}".strip()
    return d


def main():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    shutil.copy2(PLAN, PLAN.with_name("plan.json.bak_antes_diseno_guion"))

    # Los "avisos" del plan anterior describian el diseño basado en el PDF
    # (colores que el PDF nombraba, intensidades relativas, y la nota falsa de
    # que el effect 7 no se podia escribir por telnet). Este diseño los
    # reemplaza, asi que no se arrastran: van los nuevos.
    nuevos = []
    for cue in (f"Q{i}" for i in range(1, 54)):
        escena, momento, spec, razon = C[cue]
        grupos = {}
        for item in spec:
            if item[0] == "COB":
                # El Par COB II no se mixeda: el color se escribe con los
                # atributos del preset CÁLIDO (COLORRGB18=100 / COLORRGB5=0).
                cob = grupo(40, None)
                cob["attrs"] = dict(COB_ATTRS)
                cob["bruto"] = "40% Cálido (COB frontal de cabina)"
                grupos["COB"] = cob
                continue
            if item[0] == "alt":
                # intercalado cian/dorado fixture por fixture en las barras
                _, colores, dim = item
                for barra in ("BT", "BM"):
                    grupos[barra] = grupo(dim, None, alt=colores)
                continue
            if item[0] == "cruz":
                # un color de RUEDA por cabezal (COLOR1), cicla la lista.
                # Es lo que hace posible el arcoiris con 4 cabezales y la
                # cuenta regresiva de "se van losing los colores".
                _, colores, dim, ef = item
                grupos["CM"] = grupo(dim, None, efecto=ef, rueda_alt=colores)
                continue
            if item[0] == "cabeza":
                # cabezales con POSICION fija (PAN/TILT de CABEZAS_PT) y sin
                # barrido: el haz se queda donde se lo apunta. Se usa en el
                # baile de la escena 2, donde el operador quiere los cabezales
                # prendidos y apuntando hacia abajo, no cruzando.
                # El color va SIEMPRE explicito: sin esto el cabezal hereda
                # el color del cue anterior (fallo silencioso, lo atrapa el
                # guard de build_sequences.py).
                _, color, dim, ef = item
                grupos["CM"] = grupo(dim, color, efecto=ef,
                                     pt=CABEZAS_PT)
                continue
            g, dim, color, ef = item
            grupos[g] = grupo(dim, color, ef)

        # El operador pidio PAN/TILT para los cabezales en TODA la obra, no solo
        # en algunos cues: asi que cualquier grupo CM que haya quedado sin
        # posicion recibe CABEZAS_PT. Donde hay ef17 el barrido manda sobre el
        # valor estatico y esto queda de referencia; donde no hay barrido (los
        # congelados, el baile), el valor ES la posicion.
        if "CM" in grupos and not grupos["CM"].get("pt"):
            grupos["CM"]["pt"] = [list(p) for p in CABEZAS_PT]
            grupos["CM"]["avisos"].append(
                "posicion PAN/TILT por cabezal: "
                + " / ".join(f"fx{i+1}(p{a},t{b})"
                             for i, (a, b) in enumerate(CABEZAS_PT)))

        # snaps declarados en el razonamiento de cada cue
        if cue in CUES_CON_SNAP:
            for g in grupos.values():
                g["snap"] = True

        avisos = []
        nuevos.append({
            "cue": cue, "scene": escena, "momento": momento,
            "grupos": grupos,
            "avisos": avisos,
            "guion": razon,
        })

    PLAN.write_text(json.dumps(nuevos, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"backup: plan.json.bak_antes_diseno_guion")
    print(f"cues generados: {len(nuevos)}")
    for n in nuevos:
        gs = " ".join(f"{g}:{c['dim']}"
                      f"{'/c' + c['color'] if c.get('color') else ''}"
                      f"{'/e' + str(c['efecto']) if c.get('efecto') else ''}"
                      for g, c in n["grupos"].items())
        print(f"  {n['cue']:>3}  {gs}")


# cues donde el texto del guion pide un cambio instantáneo
CUES_CON_SNAP = {"Q4", "Q35", "Q36"}

if __name__ == "__main__":
    main()
