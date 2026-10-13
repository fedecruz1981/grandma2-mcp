r"""
Arma el paquete para subir a Google Drive y calcula las tandas de subida.

Por que: la subida se hace por el `<input type=file>` de Drive, que deja los
archivos PLANOS en la carpeta abierta, sin estructura. Por eso el paquete se
arma con prefijos numerados (01_show_, 02_fuente_, ...) para que en Drive queden
ordenados por nombre.

Ademas calcula las tandas porque la herramienta de subida tiene dos topes: 8
archivos por llamada y 5 MiB por llamada. El paquete completo pasa de 5 MiB, asi
que sale en varias tandas.

Que va y por que (lo agreed con el operador):
  - el show ACTUAL de la consola: es lo unico que se restaura en una consola
  - los 5 backups de data/: historial de cambios
  - data/: la fuente (plan.json es de donde sale todo el diseno)
  - los XML de la consola (chk_*) y los que genera el build (build_*)
  - los scripts que tocan la obra (no los 167 que hay, que son ruido)
  - los 2 reportes de ensayo

NO sube nada: solo deja el lote armado en data/drive_lote y escribe
data/drive_lote/tandas.json con el plan de tandas.

Uso: python scripts\empaquetar_drive.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
LOTE = DATA / "drive_lote"
SHOWS = Path(r"C:\ProgramData\MA Lighting Technologies"
             r"\grandma\gma2_V_3.9.60\shows")
EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies"
              r"\grandma\gma2_V_3.9.60\importexport")

SHOW_ACTUAL = "inti y luna oct2026.show.gz"
LIMITE_ARCHIVOS = 8
LIMITE_BYTES = 5 * 1024 * 1024

# Scripts que tocan la obra. Los otros ~140 de scripts/ son pruebas de una vez
# que ya no hacen falta para reconstruir el diseno.
CODIGO = [
    # --- la cadena que genera e importa
    "ma2_telnet.py",            # cliente telnet (todo el trabajo va por aca)
    "seqxml.py",                # genera el XML de la secuencia
    "build_sequences.py",       # arma + importa + verifica (--dry, --escena N)
    "generar_diseno_guion.py",  # genera data/plan.json desde el guion
    # --- verificacion
    "verificacion_final.py",    # end-to-end: secuencias + botones
    "ver_stomps.py",            # cuenta los stomp en el export real
    "ver_reglas_fondo.py",      # negro / congelados / escena 2 sin color / COB
    "ver_pan_tilt_grabado.py",
    "ver_arco_cabezales.py",
    "ver_pan_tilt.py",
    "ver_efecto_barrido.py",
    # --- como se averiguo el stomp (documenta el hallazgo)
    "probar_stomp_en_secuencia.py",
    "sondar_stomp.py",
    "buscar_macro_stomp.py",
    "ver_macro_stomp.py",
    # --- reportes
    "reporte.py",
    "reporte_diseno.py",
    "cue_report.py",
    # --- utileria
    "pdf_cues.py",              # lee los cues del PDF
    "wheel_map.py",             # mapeo de la rueda de color
    "export_seq.py",
    "dump_efecto_crudo.py",
    "sondar_pan_tilt.py",
    "cleanup_scratch.py",
]

FUENTE = [
    "plan.json",                # FUENTE DE VERDAD de los 53 cues
    "guion_raw.txt",            # el guion completo
    "pdf_cues.json",            # los cues tal como salen del PDF
    "pdf_notas.md",
    "diseno_guion.json",        # el diseno ya expandido
    "rig.json",                 # patch
    "wheel_map.json",           # rueda de color
    "palette.md",
    "layout.md",
    "executors.md",
    "cues.json",                # dump de cues de la consola
    "cues_report.txt",
    "_attrs.txt",               # dumps de referencia de la consola
    "_effects.txt",
    "backup_humo_contexto.txt",
]

LEEME = """INTI Y LUNA - PAQUETE DE RESPALDO
====================================

Fecha del corte: {fecha}
Consola: grandMA2 3.9.60, show "{show}" ({tam_show})

COMO ESTA ORDENADO
------------------
La subida de Drive deja los archivos planos en una carpeta, asi que el prefijo
numerado es el orden:

  00_LEEME.txt            este archivo
  01_show_ACTUAL__        el show que estaba abierto. ES EL MAESTRO.
  01_show_HISTORIA__      los 5 backups previos
  02_fuente__             de donde sale el diseno (plan.json es la clave)
  03_xml_consola__        lo que la consola tiene realmente adentro (chk_*)
  04_xml_generado__       lo que genera build_sequences.py (build_*)
  05_codigo__             los scripts que reconstruyen y verifican todo
  06_reporte__            las tablas de ensayo por escena

LO IMPORTANTE DE VERDAD
----------------------
01_show_ACTUAL__inti_y_luna_oct2026.show.gz es lo UNICO que se puede abrir en
una consola. Lleva el patch, los presets, los macros, los botones y las otras
149 secuencias que no se tocaron. Si se pierde, no hay forma de reconstruirlo.

Los XML (03 y 04) son DERIVADOS: se regeneran desde 02_fuente__plan.json. Sirven
para comparar o reimportar sin la consola, no para restaurar un show.

COMO RECONSTRUIR EL DISENO
--------------------------
1. Copiar el show a la carpeta de shows de grandMA2 y abrirlo.
2. Instalar Python 3 con las dependencias de 05_codigo__ma2_telnet.py.
3. cd al proyecto; edit la constante GMA_HOST en el .cmd que llama a Python.
4. python scripts\\generar_diseno_guion.py     -> regenera data/plan.json
5. python scripts\\build_sequences.py --dry     -> muestra el plan sin tocar nada
6. python scripts\\build_sequences.py           -> importa las 6 secuencias
7. python scripts\\verificacion_final.py        -> tiene que decir OK en las 6
8. python scripts\\ver_stomps.py                -> tiene que decir 820/820

OJO CON build_sequences.py: REESCRIBE la secuencia entera, asi que cualquier
cue agregado a mano en la consola se borra al correrlo. Ver la nota de abajo.

ESTADO AL CERRAR ESTE PAQUETE
-----------------------------
Las 6 secuencias de la obra verificadas OK, y los 820 stomp verificados cue por
cue contra el export real de la consola. Sin cues en negro, congelados en azul
hielo 5/5, escena 2 sin color (solo blanco y gris), COB al 40% salvo en escena 2.
Botones 3.101 a 3.106 en Go sobre las 6 secuencias.

LA SECUENCIA 156 TIENE UN CUE MAS QUE EL PLAN
---------------------------------------------
Al cierre, seq 156 (E1 POR VOS) tiene 6 cues y el plan solo describe 5: el
cue 6 fue agregado a mano en la consola DESPUES de la ultima importacion, y es
del operador. Esta en el show y en 03_xml_consola__chk_156.xml, pero NO esta en
02_fuente__plan.json: la proxima vez que se corra build_sequences.py se va a
perder. Si hay que conservarlo, primero hay que meterlo al plan.
"""


def tam(p: Path) -> int:
    return p.stat().st_size if p.exists() else 0


def main() -> int:
    if LOTE.exists():
        shutil.rmtree(LOTE)
    LOTE.mkdir(parents=True)

    plan: list[tuple[str, Path]] = []      # (nombre en el lote, origen)

    # ---- 00 documentos de traspaso y contexto
    traspaso = DATA / "HANDOVER_inti_y_luna.md"
    if traspaso.exists():
        plan.append(("00_HANDOVER__intiy_luna_traspaso.md", traspaso))
    else:
        print(f"  (falta el traspaso: {traspaso})")

    contexto = DATA / "CONTEXTO_inti_y_luna.md"
    if contexto.exists():
        plan.append(("00_CONTEXTO__proyecto_inti_y_luna.md", contexto))
    else:
        print(f"  (falta el contexto: {contexto})")

    # ---- 01 show actual + historial
    actual = SHOWS / SHOW_ACTUAL
    if not actual.exists():
        print(f"ERROR: no encuentro el show {actual}")
        return 1
    plan.append(("01_show_ACTUAL__inti_y_luna_oct2026.show.gz", actual))
    for b in sorted(DATA.glob("*.show.gz")):
        plan.append((f"01_show_HISTORIA__{b.name}", b))

    # ---- 02 fuente
    for n in FUENTE:
        p = DATA / n
        if p.exists():
            plan.append((f"02_fuente__{n}", p))
        else:
            print(f"  (falta en data/: {n})")

    # ---- 03/04 XML
    for seq in range(156, 162):
        for pre, pref in (("chk", "03_xml_consola"),
                          ("build", "04_xml_generado")):
            p = EXPORT / f"{pre}_{seq}.xml"
            if p.exists():
                plan.append((f"{pref}__{pre}_{seq}.xml", p))
            else:
                print(f"  (falta el XML: {p.name})")

    # ---- 05 codigo
    for n in CODIGO:
        p = HERE / n
        if p.exists():
            plan.append((f"05_codigo__{n}", p))
        else:
            print(f"  (falta el script: {n})")

    # ---- 06 reportes
    for n in ("diseno_luces_guion.md", "reporte_operador.md"):
        p = DATA / n
        if p.exists():
            plan.append((f"06_reporte__{n}", p))

    # ---- copiar
    import datetime
    total = 0
    for nombre, origen in plan:
        destino = LOTE / nombre
        shutil.copy2(origen, destino)
        total += destino.stat().st_size

    leeme = LOTE / "00_LEEME.txt"
    leeme.write_text(
        LEEME.format(fecha=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                     show=SHOW_ACTUAL,
                     tam_show=f"{tam(actual)/1024:.0f} KB"),
        encoding="utf-8")
    total += leeme.stat().st_size

    # ---- tandas: 8 archivos y 5 MiB por llamada
    archivos = sorted(LOTE.iterdir(), key=lambda p: p.name)
    tandas, cur, cur_bytes = [], [], 0
    for p in archivos:
        b = p.stat().st_size
        if cur and (len(cur) >= LIMITE_ARCHIVOS
                    or cur_bytes + b > LIMITE_BYTES):
            tandas.append(cur)
            cur, cur_bytes = [], 0
        cur.append(p)
        cur_bytes += b
    if cur:
        tandas.append(cur)

    (DATA / "drive_lote_tandas.json").write_text(
        json.dumps([[str(p) for p in t] for t in tandas], indent=1),
        encoding="utf-8")

    # ---- informe
    print()
    print("=" * 74)
    print("PAQUETE ARMADO")
    print("=" * 74)
    grupo = ""
    for nombre, _ in plan:
        g = nombre.split("_")[0] + "_" + "_".join(nombre.split("_")[1:3])
        if g != grupo:
            grupo = g
            print(f"\n  {nombre[:3]} {g}")
        print(f"      {nombre:<58} {tam(LOTE / nombre)/1024:>8.0f} KB")
    print(f"\n      {'00_LEEME.txt':<58} {tam(leeme)/1024:>8.0f} KB")
    print()
    print(f"  {len(archivos)} archivos, {total/1024/1024:.2f} MB "
          f"en {LOTE}")
    print(f"  {len(tandas)} tandas de subida "
          f"(tope: {LIMITE_ARCHIVOS} archivos / "
          f"{LIMITE_BYTES//1024//1024} MiB por tanda)")
    for i, t in enumerate(tandas, 1):
        kb = sum(p.stat().st_size for p in t) / 1024
        print(f"      tanda {i}: {len(t)} archivos, {kb:.0f} KB")
    print()
    print("  plan de tandas en data/drive_lote_tandas.json")
    print("  (este script NO sube nada: la subida la hace el navegador)")
    return 0


if __name__ == "__main__":
    sys.exit(main())