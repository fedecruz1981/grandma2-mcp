r"""
Cambia la funcion de boton del executor 3.101 de Flash a Go.

Por que: la escena 1 completa (5 cues) quedo en el boton 3.101, y con Flash la
secuencia corre sola cue por cue sin poder detenerse. La escena 1 tiene dos
momentos que no se pueden perder (Q3 la interaccion con el publico, Q4 el
congelamiento de Luna), asi que necesita ir con Go, como los otros 5 botones.

Sintaxis del repo: `asignar_flash_101.py` puso Flash con
    Assign Flash At Executor 3.101
y `fix_scene_buttons.py` pone Go con
    Assign Go At Executor 3.101

Ojo: `Assign Go At Executor` podría vaciar la secuencia asignada. Por eso este
script NO se queda con el "ok" del comando: exporta el executor ANTES y DESPUES
y verifica que (a) la funcion quedo en Go y (b) la secuencia 156 sigue asignada.
Si se perdio, la reasigna.

Despues guarda el show.

Uso:
    python scripts\cambiar_101_go.py
    python scripts\cambiar_101_go.py --revertir     # vuelve a Flash
"""
import asyncio
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402

EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")
BOTON = "3.101"
SEQ_ESPERADA = "156"
CODIGO = {"Go": "12299", "Flash": "12302", "Toggle": "12307",
          "Temp": "12291", "On": "12293", "Off": "12290"}


async def exportar(ma2, tag):
    """Exporta el executor y devuelve (secuencias asignadas, codigo de boton)."""
    f = EXPORT / f"{tag}.xml"
    f.unlink(missing_ok=True)
    await ma2.cmd("cd /")
    r = await ma2.cmd(f'Export Executor {BOTON} "{tag}"')
    for _ in range(15):
        if f.exists() and f.stat().st_size > 0:
            break
        await asyncio.sleep(0.3)
    if not (f.exists() and f.stat().st_size > 0):
        return None, None, r.errors
    txt = f.read_text(encoding="utf-8", errors="replace")
    nos = re.findall(r"<No>(\d+)</No>", txt)
    btn = re.search(r"<Button>(\d+)</Button>", txt)
    nombre = re.search(r'Assignment name="([^"]+)"', txt)
    f.unlink(missing_ok=True)
    return nos, (btn.group(1) if btn else None), nombre


def func_por_codigo(cod):
    for k, v in CODIGO.items():
        if v == cod:
            return k
    return f"?({cod})"


async def main():
    revertir = "--revertir" in sys.argv
    destino = "Flash" if revertir else "Go"
    print(f"cambio pedido: 3.101 -> {destino}")
    print(f"host: {__import__('os').environ.get('GMA_HOST','(default 192.168.0.71)')}")
    print()

    async with Ma2() as ma2:
        await ma2.at_prompt()

        print("=" * 70)
        print("ANTES")
        print("=" * 70)
        nos0, cod0, nom0 = await exportar(ma2, "bot101_antes")
        print(f"  secuencia asignada : {nos0}")
        print(f"  funcion de boton   : {func_por_codigo(cod0)} ({cod0})")
        print(f"  nombre             : {nom0.group(1) if nom0 else '(vacio)'}")
        if cod0 is None:
            print("  no se pudo exportar el executor; no toco nada")
            return

        print()
        print("=" * 70)
        print(f"COMANDO: Assign {destino} At Executor {BOTON}")
        print("=" * 70)
        await ma2.cmd("cd /")
        r = await ma2.cmd(f"Assign {destino} At Executor {BOTON}")
        for ln in [x for x in r.lines if x.strip()]:
            print(f"  respuesta cruda: {ln.strip()[:110]}")
        if r.errors:
            for e in r.errors:
                print(f"  ERROR: {e}")
        else:
            print("  (sin errores)")

        print()
        print("=" * 70)
        print("DESPUES")
        print("=" * 70)
        nos1, cod1, nom1 = await exportar(ma2, "bot101_despues")
        print(f"  secuencia asignada : {nos1}")
        print(f"  funcion de boton   : {func_por_codigo(cod1)} ({cod1})")
        print(f"  nombre             : {nom1.group(1) if nom1 else '(vacio)'}")

        ok = cod1 == CODIGO[destino]
        print()
        if not ok:
            print(f"  LA FUNCION NO QUEDO EN {destino.upper()}")
        else:
            print(f"  OK: la funcion quedo en {destino}")
        if SEQ_ESPERADA not in (nos1 or []):
            print(f"  se perdio la secuencia {SEQ_ESPERADA}: reasigno")
            await ma2.cmd("cd /")
            rr = await ma2.cmd(f"Assign Sequence {SEQ_ESPERADA} Executor {BOTON}")
            print(f"  >>> Assign Sequence {SEQ_ESPERADA} Executor {BOTON} "
                  f"err={rr.errors}")
            await ma2.cmd("cd /")
            rr = await ma2.cmd(f"Assign {destino} At Executor {BOTON}")
            print(f"  >>> Assign {destino} At Executor {BOTON} err={rr.errors}")
            nos1, cod1, nom1 = await exportar(ma2, "bot101_reasignado")
            print(f"  secuencia : {nos1}   funcion: {func_por_codigo(cod1)}")
            ok = ok and SEQ_ESPERADA in (nos1 or [])
        else:
            print(f"  OK: la secuencia {SEQ_ESPERADA} sigue asignada")

        await ma2.cmd("cd /")
        r = await ma2.cmd("SaveShow /noconfirm")
        print()
        for ln in [x for x in r.body if x.strip()][:2]:
            print(f"  {ln.strip()[:110]}")

        print()
        print("RESULTADO:", "TODO OK" if ok else "REVISAR")


if __name__ == "__main__":
    asyncio.run(main())
