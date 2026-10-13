r"""
Lee el patch de los cabezales (fx1-4) con nombres de archivo UNICOS.

Por que nombres unicos: `Export Fixture 1 'fixture1'` SI funciona en esta
consola, pero si el archivo ya existe la consola abre un dialogo modal de
Overwrite y a partir de ahi TODO comando responde `Invalid Key`. Con un nombre
distinto en cada corrida no hay colision y nunca aparece el dialogo.

Tambien responde si el movil tiene capas apagadas.

Solo lectura: exporta a XML y borra lo que exporto.

Uso: python scripts\ver_patch_cabezales.py
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
from ma2_telnet import ANSI  # noqa: E402

EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")


async def mandar(ma2, cmd, espera=4.0):
    """Manda un comando crudo y devuelve las lineas limpias."""
    await ma2.drain()
    await ma2._raw(cmd)
    crudo = await ma2._read_until_prompt(max_wait=espera)
    txt = ANSI.sub("", crudo or "")
    return [ln.strip() for ln in txt.replace("\r", "\n").split("\n") if ln.strip()]


async def main():
    sello = f"{int(time.time()) % 100000:05d}"
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")
    print(f"sello de corrida: {sello}  (nombres unicos -> sin dialogo de overwrite)")

    async with Ma2() as ma2:
        # Si quedo un dialogo de una corrida anterior, se cancela.
        for _ in range(4):
            lineas = await mandar(ma2, "cd /", espera=3.0)
            if any("Overwrite" in x for x in lineas):
                print("\n  habia un dialogo de Overwrite colgado: respondo 2 (Cancel)")
                await mandar(ma2, "2", espera=3.0)
                continue
            break

        # ------------------------------------------------------------------
        print()
        print("=" * 76)
        print("1. PATCH DE fx1..fx4  (nombre real, tipo, canal, capas)")
        print("=" * 76)
        for fx in (1, 2, 3, 4):
            tag = f"prb_cz{fx}_{sello}"
            f = EXPORT / f"{tag}.xml"
            await mandar(ma2, f"Export Fixture {fx} '{tag}'")
            for _ in range(24):
                if f.exists() and f.stat().st_size > 0:
                    break
                await asyncio.sleep(0.25)
            if not (f.exists() and f.stat().st_size > 0):
                print(f"\n  fx{fx}: no se genero {tag}.xml")
                continue
            txt = f.read_text(encoding="utf-8", errors="replace")
            f.unlink(missing_ok=True)

            nombres = re.findall(r"<Name>([^<]*)</Name>", txt)
            tipo = re.findall(r"FixtureType=\"([^\"]*)\"", txt) \
                or re.findall(r"<FixtureType>([^<]*)</FixtureType>", txt)
            univ = re.findall(r"Universe=\"?(\d+)", txt)
            addr = re.findall(r"Address=\"?(\d+)", txt)
            capas = re.findall(r"Layer(?:Number)?=\"?(\d+)", txt)
            capas2 = re.findall(r"<Layer[^>]*>(\d+)</Layer>", txt)
            capas_on = re.findall(r"Layer(?:Number)?=\"?(\d+)[^>]*?(?:At|Value)=\"?(\d+)",
                                  txt)
            print(f"\n  --- fx{fx}  ({len(txt)} bytes de XML)")
            if nombres:
                print(f"      nombre(s): {nombres[:4]}")
            if tipo:
                print(f"      tipo     : {sorted(set(tipo))[:3]}")
            if univ:
                print(f"      universo  : {sorted(set(univ))[:4]}")
            if addr:
                print(f"      direccion : {sorted(set(addr))[:4]}")
            if capas or capas2:
                print(f"      capas     : {sorted(set(capas + capas2))}")
            if capas_on:
                print(f"      capa@valor: {sorted(set(capas_on))}")
            if not (nombres or tipo or univ or addr):
                print("      (el XML no trae patch legible; se muestra entero abajo)")
                for ln in txt.splitlines():
                    if ln.strip():
                        print(f"        {ln.strip()[:112]}")

        # ------------------------------------------------------------------
        print()
        print("=" * 76)
        print("2. CAPA DE CADA CABEZAL (via el prompt de Fixture N)")
        print("=" * 76)
        for fx in (1, 2, 3, 4):
            lineas = await mandar(ma2, f"cd / Fixture {fx}")
            capa = next((x for x in lineas if "Layer" in x or "layer" in x), "")
            print(f"  fx{fx}: {capa[:112] if capa else lineas}")

        # ------------------------------------------------------------------
        print()
        print("=" * 76)
        print("3. LAS CAPAS ESTAN ENCENDIDAS?  (capas de LiveSetup)")
        print("=" * 76)
        for cmd in ("list layer", "Layer", "cd / Layer 4",
                    "at 100 layer 4", "Layer 4 at 0"):
            lineas = await mandar(ma2, f"cd / {cmd}", espera=3.5)
            print(f"\n  >>> {cmd}")
            for ln in lineas[:8]:
                print(f"      {ln[:112]}")

        await mandar(ma2, "cd / Clear")


if __name__ == "__main__":
    asyncio.run(main())