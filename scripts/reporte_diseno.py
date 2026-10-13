r"""
Genera data/diseno_luces_guion.md: la propuesta de diseño leída del guion y el
comparativo celda por celda contra el diseño anterior (basado en el PDF de cues).

El "anterior" se toma de data/plan.json.bak_diseno_guion_<fecha>, que es el
plan tal como estaba antes de este trabajo. OJO: el backup que hace el propio
generador (plan.json.bak_antes_diseno_guion) se sobrescribe en cada corrida, así
que no sirve para comparar.

Uso: python scripts/reporte_diseno.py
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
ORDEN = ["CM", "BT", "FRONT", "BM", "BF", "COB"]
SEQ_BASE = 155
BOTON = {1: "3.101", 2: "3.102", 3: "3.103", 4: "3.104", 5: "3.105", 6: "3.106"}
FIXTURES = {"CM": "fx1-4 Beamer 250 Mini (rueda, sin RGB)",
            "BT": "fx5-8 Stromber",
            "FRONT": "fx9-14 Nebula Flat 210",
            "BM": "fx15-22 Nebula Max 162",
            "BF": "fx23-30 Protones chico",
            "COB": "fx32-34 Par COB II"}


def backup_anterior():
    cands = sorted(DATA.glob("plan.json.bak_diseno_guion*"))
    if not cands:
        raise SystemExit("no hay backup del plan anterior")
    return json.loads(cands[-1].read_text(encoding="utf-8"))


def celda(gr, cg):
    """Como se ve una celda en el reporte: nivel, color, efecto."""
    if not cg or cg.get("accion") == "nada":
        return "—"
    p = []
    if cg.get("dim") is not None:
        p.append(f"{cg['dim']}%")
    # el COB no se mixeda: su color vive en los atributos del preset
    if cg.get("attrs"):
        p.append("Cálido (attrs)")
    elif cg.get("alternar_rgb"):
        # intercalado fixture por fixture: el color ya lo define la lista
        p.append("Cian/Dorado")
    elif cg.get("color"):
        p.append(cg["color"])
    ef = cg.get("efecto")
    if ef:
        p.append(f"ef{17 if (gr == 'CM' and ef == 7) else ef}")
    return " ".join(p) if p else "?"


def main():
    nuevo = json.loads((DATA / "plan.json").read_text(encoding="utf-8"))
    viejo = {c["cue"]: c for c in backup_anterior()}

    escenas = []
    for c in nuevo:
        if c["scene"] not in escenas:
            escenas.append(c["scene"])

    cambiados = 0
    total = 0
    filas = []
    for c in nuevo:
        v = viejo.get(c["cue"], {})
        dif = []
        for g in ORDEN:
            a = celda(g, v.get("grupos", {}).get(g))
            b = celda(g, c["grupos"].get(g))
            total += 1
            if a != b:
                cambiados += 1
                dif.append(f"**{g}**: ~~{a}~~ → {b}")
        filas.append((c["cue"], c.get("momento", ""), dif))

    L = []
    L.append("# DISEÑO DE LUCES — Inti y Luna: Guerreros de la Luz")
    L.append("")
    L.append(f"Generado el {datetime.now():%Y-%m-%d %H:%M}.  ")
    L.append("Fuente del diseño: **el guion** de la obra "
             "(`Obra teatral INTI Y LUNA Guerreros de la Luz - Huayra-1.pdf`, "
             "36 págs., Guion: Francisco Rivera / Dirección: Silvia Gachy "
             "Zerda), leído completo.  ")
    L.append(f"**{len(nuevo)} cues en {len(escenas)} secuencias (156-161)**, "
             f"botones 3.101-3.106. Cambiaron **{cambiados} de {total}** celdas "
             f"respecto del diseño anterior (basado en el PDF de cues).")
    L.append("")
    L.append("> Los 53 momentos (Q1-Q53) **no se tocaron**: el guion coincide "
             "1 a 1 con el PDF de cues que ya tenías grabado, así que la "
             "estructura de la obra se mantiene y solo cambia el diseño de luz.")
    L.append("")

    # ---------------- criterios
    L += ["## Los criterios con que se decidió", ""]
    L += [
        "**1. Cada personaje tiene una luz, y el guion dice cuál.**",
        "",
        "| Personaje | Poder (según el guion) | Luz |",
        "|---|---|---|",
        "| Inti | cambia colores, transmite emociones | arcoíris que se apaga |",
        "| Luna | congela, transmite calma | blanco cálido / azul hielo |",
        "| Valkira | controla el tiempo, colores primarios | morado + amarillo |",
        "| Qoori | visión, sabiduría | dorado, luz cenital |",
        "| Lord Bigotín | sin emociones, sin colores | gris frío, blanco duro |",
        "",
        "**2. Las frases del guion que hablan de luz se respetan al pie de la "
        "letra.** No son sugerencias:",
        "",
        "| Cita del guion | Cue | Qué se grabó |",
        "|---|---|---|",
        '| *"Luces amarillas y moradas"* | Q17, Q22 | morado en barras y BM, '
        'amarillo en el resto |',
        '| *"Luces que parpadean"* / *"comienzan a titilar"* | Q3, Q4, Q27, Q32, '
        'Q34, Q41, Q45 | ef6 (Shutter PWM) |',
        '| *"La luz se apaga lentamente"* | Q30 | niveles al 30%, sin efecto |',
        '| *"Las luces titilan"* | Q46, Q47 | ef4 (Dimmer Random), irregular |',
        '| *"Las luces comienza a girar"* | Q49, Q52 | ef7 + ef2 en chase |',
        '| *"No más AZUL, no más AMARILLO, no más ROJO, no más VERDE"* | Q24 | '
        'un color por grupo, con ef7: los ve y los apaga |',
        '| *"¿Cuáles son los colores primarios?"* | Q18 | un primario por grupo '
        '(rojo / azul / amarillo) |',
        "",
        "**3. La escena 6 es el arco central de la obra: GRIS → COLOR.** "
        "Todo Q32-Q48 vive en grises; el color sólo entra a partir de Q49 "
        "(\"Penitas\"), que es donde el guion dice que la música le devuelve "
        "los colores a Colorilandia. Ese es el momento musical de la obra y "
        "por eso la progresión va de un gris casi apagado (128,132,138) al "
        "arcoíris al 100%.",
        "",
        "**4. Los colores que ya tenías se conservan; los nuevos son cinco.**",
        "",
        "Los que ya venían de tu PDF de cues se mantienen con el mismo valor "
        "RGB, así que nada de lo que aprobaste se movió de lugar. Los nuevos:",
        "",
        "| Nombre | RGB | R/G/B en la consola | Para qué |",
        "|---|---|---|---|",
        "| Gris muerto | 128,132,138 | 50.2 / 51.8 / 54.1 | el gris de \"ya no "
        "hay color\"; fundidos y el punto más bajo |",
        "| Gris pálido | 150,154,160 | 58.8 / 60.4 / 62.7 | niebla de transición, "
        "viaje temporal, el amague de color |",
        "| Indigo | 70,40,160 | 27.5 / 15.7 / 62.7 | la sombra fría de Bigotín: "
        "oscuro pero no negro, y con color propio |",
        "| Verde jade | 0,200,120 | 0 / 78.4 / 47.1 | verde de esperanza "
        "(\"jugate ya\") |",
        "| Rosa confeti | 255,140,190 | 100 / 54.9 / 74.5 | rosa suave de "
        "fiesta y romance |",
        "",
        "**5. Tus reglas se mantienen enteras.**",
        "",
        "- **Ningún cue en negro total.** Los cinco fundidos de la obra "
        "(Q8, Q21, Q30, Q31, Q36) quedan en gris al 10-35%: fundido, no apagón.",
        "- **Escena 2 sin color, solo blanco.** Verificado sobre la exportación "
        "de la consola: la saturación máxima de los 6 cues es **16,1%**, y es "
        "el blanco frío (214,232,255). Todo lo demás son grises puros. No hay "
        "ningún tono de color.",
        "- **COB al 40% en CÁLIDO** (COLORRGB18=100 / COLORRGB5=0) en las 5 "
        "escenas, y **fuera de la escena 2**, como venías pidiendo.",
        "- **Escena 3: cian intercalado con dorado, fixture por fixture, al "
        "50%** en las barras (BT y BM), en los 5 cues. Se mantiene tu pedido.",
        "- **3.101 en Flash**, no Go.",
        "- **Blinder (fx31) sin tocar.**",
        "",
    ]

    # ---------------- el arco por escena
    L += ["## El arco de cada escena", ""]
    ARCOS = [
        (1, "POR VOS", "Colorilandia es una plaza de colores y a Inti le "
         "funciona el poder... hasta que deja de funcionarle.",
         "Arcoíris radiante → el color se desatura a gris/azul frío cuando "
         "falla → parpadeo nervioso de blanco cuando intenta con el público "
         "→ azul hielo clavado cuando Luna lo congela → cálido neutro de "
         "alivio."),
        (2, "SOY LORD BIGOTIN", "La fiesta se cae y aparece el mundo de "
         "Bigotín: blanco, gris, negro. Sin colores, porque él los prohibió.",
         "Solo blancos y grises. El villano entra con blanco duro de "
         "contraluz y sombra alrededor; su monólogo va en un plano gris "
         "uniforme sin efectos; la canción es chase de intensidad con strobo "
         "en los golpes."),
        (3, "LA MIRADA DORADA", "Inti y Luna buscan a la sabia Qoori, y ella "
         "mira hacia Grisolin y ve la amenaza.",
         "El dorado entra desde el primer cue porque la escena se llama así. "
         "Cian intercalado con dorado al 50% en las barras (tu pedido). En "
         "Q16 el dorado se apaga a ámbar oscuro y entra el strobo: la luz "
         "misma se aviva del peligro."),
        (4, "REINA GITANA", "Valkira entra y el ambiente se vuelve magia y "
         "alegría gitana. Pero suelta una chispa en el corazón.",
         "Amarillos y morados, que es literalmente lo que pide el guion. La "
         "\"luz de estrella\" es el clímax: morado de Valkira con destello "
         "amarillo. Y después el morado se apaga a ámbar tenue y gris: los "
         "colores empiezan a perder brillo."),
        (5, "TODO EN GRIS ES MÁS DIVERTIDO", "Valkira lleva a Inti y Luna al "
         "pasado, ven al Bigotín bueno jardinero, y él se transforma.",
         "Oasis de color cálido en la canción de la sonrisa. El viaje en el "
         "tiempo es un glitch de strobo. El recuerdo es ámbar cálido y quieto. "
         "\"Reina Gitana\" es el dorado más luminoso de la obra. Y al volver al "
         "presente todo cae a gris al 30%: la luz se apaga lentamente, como "
         "dice el texto."),
        (6, "SI SOLAMENTE LO QUERÉS", "Colorilandia ya es gris. Los héroes "
         "llegan tarde, Bigotín se burla, ven la verdad del pasado y "
         "entonces los colores vuelven.",
         "El viaje más largo y el corazón del trabajo. Gris opresivo con "
         "indigo de sombra, el strobo masivo cuando la máquina se enciende, "
         "el gris plano y muerto cuando Colorilandia pierde el color, el "
         "ámbar latiendo cuando Inti se aplica, el amague de arcoíris "
         "dudoso a 50% y su fracaso. Y en Q49 el color regresa: primero "
         "aparece, después estalla, y el final es fiesta."),
    ]
    for i, nombre, que, como in ARCOS:
        cues = [c for c in nuevo if c["scene"] == f"ESCENA {i} - {nombre}"[:9]
                or c["scene"].startswith(f"ESCENA {i} ")]
        L += [f"### Escena {i} — {nombre}  ·  seq {SEQ_BASE + i} · botón "
              f"{BOTON[i]} · {len(cues)} cues", "",
              f"*{que}*", "", como, ""]

    # ---------------- comparativo
    L += ["---", "", "## Comparativo cue por cue", "",
          "Lo que estaba antes y lo que quedó. Los momentos son los mismos; "
          "cambia la luz.", ""]
    for cue, momento, dif in filas:
        L.append(f"**{cue} — {momento}**")
        L.append("")
        if dif:
            for d in dif:
                L.append(f"- {d}")
        else:
            L.append("- sin cambios")
        L.append("")

    # ---------------- por hacer a mano
    L += ["---", "", "## Lo que queda para hacer a mano", "",
          "Estas cosas no se pueden escribir por línea de comandos y las "
          "revisá en el show antes del ensayo general:", "",
          "1. **Dónde está cada personaje en cada momento.** El diseño no lo "
          "sabe. Los cuatro cabezales (CM) están en ef17 (barrido de haz) en "
          "casi todos los cues, pero el barrido sale de la posición que tengan "
          "los Pan/Tilt: hay que apuntarlos a la zona donde actúe cada uno.",
          "2. **Dónde apuntan las luces inferiores y traseras** (BM y BF), que "
          "son las que más pesan en la lectura de la escena. Si no las ubicás, "
          "todo se aplana.",
          "3. **Niveles finos.** Todos arrancan en valores redondos (100, 80, "
          "70, 50, 40, 30, 15). Bajalos con el EAR al nivel real de la sala.",
          "4. **El COB al 40%** de cabina: confirmá que no te lava el fondo del "
          "escenario desde la sala.",
          "5. **Las 6 transiciones de fundido** (Q8, Q21, Q30, Q31, Q36): el "
          "tiempo de fade está en default. Si querés que el fundido a gris "
          "dure más de lo que dura por defecto, hay que cargar el tiempo a mano.",
          "6. **Humo.** Está en la secuencia 20, en el botón 3.111 con función "
          "Flash. No lo toqué.",
          "",
          "---", "",
          "## Cómo se grabó, por si hay que rehacerlo", "",
          "Se generó el XML completo de cada secuencia y se importó con "
          "`Import \"build_NNN\" At Sequence NNN`, que reemplaza la secuencia "
          "entera. Después se exportó cada una y se comparó cue por cue con lo "
          "que se iba a escribir: **53 cues, 0 faltantes, 0 sobrantes**. "
          "Después se guardó el show.", "",
          "Un detalle técnico que quedó descubierto al verificar, y que está "
          "documentado en el código: el **ef6 "
          "(Shutter PWM) no se puede escribir sobre SHUTTER en el grupo BM** "
          "(fx15-22, Nebula Max 162) — la consola descarta el cue entero y el "
          "strobo se pierde en silencio. Se probaron 4 variantes y ninguna "
          "funciona; sobre DIM sí. Ahora el ef6 del BM va sobre DIM y hace el "
          "mismo parpadeo. Está en `scripts/seqxml.py` (`SIN_SHUTTER`) y se "
          "midió con `scripts/test_strobe_bm2.py`.", ""]

    salida = DATA / "diseno_luces_guion.md"
    salida.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"escrito {salida}")
    print(f"  celdas cambiadas: {cambiados}/{total}")
    print(f"  cues sin cambio: {sum(1 for _, _, d in filas if not d)}")


if __name__ == "__main__":
    main()
