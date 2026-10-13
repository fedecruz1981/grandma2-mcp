r"""
Por que los cabezales no encienden / cuales son los cabezales.

Lo que ya se sabe:
  - El DIM de fx1-4 SI esta grabado en los 53 cues (min 10, max 100).
  - fx1 esta en LiveSetup/Layers 4/.
  - fx1 tiene DIM (attr 1, canal fisico 46, CONTROL->ASSERT) y PAN/TILT.
    SHUTTER (attr 18) figura como atributo SIN usar -> no le llega canal DMX.
  - NO hay ningun PAN/TILT de posicion guardado en ninguna secuencia.

Lo que este script responde:
  A. Que aparatos hay realmente en el patch, y cuales son los moviles.
     (por si los "cabezales" del operador no son fx1-4)
  B. En que capa esta cada movil, y si esa capa esta encendida.
  C. Si existe un canal de obturador/lampada en el perfil que quede cerrado.

Todo de solo lectura: exporta a XML y no modifica el show.

Uso: python scripts\diag_cabezales2.py
"""
import asyncio
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402

EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")

# fx1-4 son los que hoy llamamos CM (Beamer 250 Mini)
CANDIDATOS = (1, 2, 3, 4)


async def exportar(ma2, cmd, tag):
    """Exporta y devuelve el texto del XML (o None)."""
    f = EXPORT / f"{tag}.xml"
    f.unlink(missing_ok=True)
    await ma2.cmd("cd /")
    r = await ma2.cmd(cmd)
    for _ in range(20):
        if f.exists() and f.stat().st_size > 0:
            break
        await asyncio.sleep(0.25)
    if f.exists() and f.stat().st_size > 0:
        txt = f.read_text(encoding="utf-8", errors="replace")
        f.unlink(missing_ok=True)
        return txt, r.errors
    return None, r.errors


async def main():
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")
    async with Ma2() as ma2:
        await ma2.at_prompt()

        # ------------------------------------------------------------------
        print("=" * 74)
        print("A. QUE EXPORTES DE PATCH/FIXTURE ACEPTA LA CONSOLA")
        print("=" * 74)
        intentos = [
            ("fixtures", "Export Fixtures 'fixtures'"),
            ("fixture1", "Export Fixture 1 'fixture1'"),
            ("patch", "Export Patch 'patch'"),
            ("livesetup", "Export LiveSetup 'livesetup'"),
            ("layer4", "Export Layer 4 'layer4'"),
        ]
        guardados = {}
        for etiqueta, cmd in intentos:
            txt, err = await exportar(ma2, cmd, etiqueta)
            print(f"  Export {etiqueta:<10} -> {'ARCHIVO' if txt else 'nada':<8} "
                  f"errores={err}")
            if txt:
                guardados[etiqueta] = txt
        if guardados:
            for etiqueta, txt in guardados.items():
                print(f"\n  --- {etiqueta}.xml : primeras lineas con fixture/capa")
                for ln in txt.splitlines():
                    if re.search(r"fixture|layer|Layer|Universe|Address|<Name>",
                                 ln):
                        print(f"      {ln.strip()[:118]}")
        else:
            print("\n  ningun export de patch/fixture existe en esta consola.")
            print("  paso a leer el estado por comandos.")

        # ------------------------------------------------------------------
        print()
        print("=" * 74)
        print("B. FIXTURE 1..4: atributo x atributo (canal, rango, uso)")
        print("=" * 74)
        for fx in CANDIDATOS:
            await ma2.cmd("cd /")
            await ma2.cmd(f"Fixture {fx}")
            r = await ma2.cmd("list attribute")
            filas = []
            for ln in r.lines:
                s = ln.strip()
                if not s.startswith("Attribute "):
                    continue
                if " Off" in s and "On" not in s.split(" Off")[0]:
                    continue
                filas.append(s)
            print(f"\n  --- fx{fx} : {len(filas)} atributos en uso")
            for s in filas[:14]:
                print(f"      {s[:118]}")

        # ------------------------------------------------------------------
        print()
        print("=" * 74)
        print("C. CAPA DE CADA CABEZAL (esta o no la capa encendida)")
        print("=" * 74)
        await ma2.cmd("cd /")
        for fx in CANDIDATOS:
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"Fixture {fx}")
            echo = [x.strip() for x in r.lines if x.strip()]
            capa = ""
            for x in echo:
                m = re.search(r"Layers?\s*([\d.]+)", x)
                if m:
                    capa = m.group(1)
            print(f"  fx{fx}: capa={capa or '(no encontrada)'}   "
                  f"eco={echo[:1]}")

        # ------------------------------------------------------------------
        print()
        print("=" * 74)
        print("D. CAPAS: la 4 esta encendida? (capas de LiveSetup)")
        print("=" * 74)
        for cmd in ("list layer", "Layer 4", "cd Layer 4",
                    "list layers", "at 100 layer 4"):
            await ma2.cmd("cd /")
            r = await ma2.cmd(cmd)
            print(f"\n  >>> {cmd}")
            for ln in [x for x in r.lines if x.strip()][:6]:
                print(f"      {ln.strip()[:112]}")
            for e in r.errors:
                print(f"      ERROR: {e}")

        # ------------------------------------------------------------------
        print()
        print("=" * 74)
        print("E. VALOR LIVE del canal 46 (DIM de fx1) ahora mismo")
        print("=" * 74)
        for cmd in ("Fixture 1 At 46", "Fixture 1 At 0",
                    "Channel 46", "at 46"):
            await ma2.cmd("cd /")
            r = await ma2.cmd(cmd)
            print(f"\n  >>> {cmd}")
            for ln in [x for x in r.lines if x.strip()][:6]:
                print(f"      {ln.strip()[:112]}")

        await ma2.cmd("cd /")
        await ma2.cmd("Clear")


if __name__ == "__main__":
    asyncio.run(main())