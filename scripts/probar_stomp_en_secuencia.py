r"""
PRUEBA DECISIVA: ¿el stomp queda guardado en la secuencia, o es solo estado en vivo?

Contexto: `list macro` mostró 7 macros de stomp. El 6 "Stomp running Effects"
es `ClearSelection` + `Stomp PresetType Thru`, y la consola lo describe como
"Stomps all running effects" — sin selección pisa TODOS los efectos corriendo.

Antes se intentó escribir stomp en el XML de la secuencia (atributo en Value, en
CueData, en Cue, y como elemento <Stomp/>). La consola lo descartó en silencio
en los cuatro casos, así que el stomp no parece viajar en la secuencia.

Para confirmarlo de una vez: se graban DOS cues en la misma secuencia de prueba
con el mismo atributo y el mismo efecto de fondo:
  - cue 2: se corre `Stomp PresetType Thru` y despues se graba el valor
  - cue 3: se graba el valor sin correr el stomp (control)
Si los dos cues quedan idénticos en el XML, el stomp NO es representable en la
secuencia: es una operación en vivo. Si difieren, aparece la representación.

También consulta qué comandos de parada de efectos acepta la consola.

Uso: python scripts\probar_stomp_en_secuencia.py
"""
import asyncio
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
SEQ = 190


async def crudo(ma2, cmd, espera=6.0):
    await ma2.drain()
    await ma2._raw(cmd)
    buf = await ma2._read_until_prompt(max_wait=espera)
    txt = ANSI.sub("", buf or "")
    if "Overwrite" in txt:
        await ma2.drain()
        await ma2._raw("2")
        await ma2._read_until_prompt(max_wait=3.0)
        return "(Overwrite -> 2)", []
    lines = [x.rstrip() for x in txt.replace("\r", "\n").split("\n") if x.strip()]
    return "\n".join(lines), lines


async def main():
    sello = int(time.time()) % 100000
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")

    async with Ma2() as ma2:
        # ---------------- 1. ¿qué comandos de parada acepta? ----------------
        print()
        print("=" * 78)
        print("1. COMANDOS DE PARADA / STOMP QUE ACEPTA LA CONSOLA")
        print("=" * 78)
        for cmd in ("Stop ?", "Stomp ?", "Stomp PresetType Thru"):
            txt, lines = await crudo(ma2, cmd)
            err = [x for x in lines if re.search(r"Error", x, re.I)]
            print(f"\n  >>> {cmd}")
            for ln in txt.splitlines():
                if ln.startswith("Executing"):
                    continue
                print(f"      {ln}")
            print(f"      -> {'ERROR: ' + err[0] if err else 'aceptado'}")

        # ---------------- 2. grabar cue con stomp vs sin stomp -------------
        print()
        print("=" * 78)
        print("2. GRABAR CUE 2 (con stomp) Y CUE 3 (sin stomp, control)")
        print("=" * 78)
        pasos = [
            "cd /", "Clear",
            "Fixture 5",
            # cue 1: valor + efecto 2 (Dimmer Chase) en DIM
            "At 50", "At Effect 2",
            "Store Cue 1 Sequence 190 /noconfirm",
            # --- cue 2: primero el stomp, despues el valor ---
            "Stomp PresetType Thru",
            "At 80",
            "Store Cue 2 Sequence 190 /noconfirm",
            # --- cue 3: mismo valor, SIN stomp (control) ---
            "At 80",
            "Store Cue 3 Sequence 190 /noconfirm",
        ]
        for c in pasos:
            txt, lines = await crudo(ma2, c, espera=4.0)
            err = [x for x in lines if re.search(r"Error", x, re.I)]
            marca = f"   ERROR: {err[0]}" if err else ""
            print(f"  >>> {c}{marca}")

        # ---------------- 3. exportar y comparar ---------------------------
        print()
        print("=" * 78)
        print("3. EXPORTAR Y COMPARAR CUE 2 vs CUE 3")
        print("=" * 78)
        dst = EXPORT_DIR / f"stcmp_{sello}.xml"
        dst.unlink(missing_ok=True)
        await crudo(ma2, "cd /")
        await crudo(ma2, f'Export Sequence {SEQ} "stcmp_{sello}"')
        for _ in range(25):
            if dst.exists() and dst.stat().st_size > 0:
                break
            await asyncio.sleep(0.3)
        await crudo(ma2, "cd /")
        await crudo(ma2, "Clear")
        await crudo(ma2, f"Delete Sequence {SEQ}")
        print(f"  secuencia {SEQ} de prueba borrada")

        if not (dst.exists() and dst.stat().st_size > 0):
            print("  no se pudo exportar")
            return 1
        txt = dst.read_text(encoding="utf-8", errors="replace")
        dst.unlink(missing_ok=True)

        def bloque(n):
            i = txt.find(f'<Cue index="{n}"')
            j = txt.find('<Cue index=', i + 10)
            return txt[i:j if j > 0 else len(txt)]

        c2, c3 = bloque(2), bloque(3)
        print()
        print("--- cue 2 (CON stomp) ---")
        for ln in c2.splitlines():
            if ln.strip():
                print(f"      {ln.strip()}")
        print("--- cue 3 (SIN stomp, control) ---")
        for ln in c3.splitlines():
            if ln.strip():
                print(f"      {ln.strip()}")

        print()
        if c2.strip() == c3.strip():
            print("VEREDICTO: los dos cues quedaron IDENTICOS.")
            print("  -> el stomp NO se guarda en la secuencia. Es estado en vivo.")
        else:
            print("VEREDICTO: los cues DIFIEREN. El stomp SÍ se guarda:")
            print("  -> la diferencia de arriba es la representacion a usar.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))