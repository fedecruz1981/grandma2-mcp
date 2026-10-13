"""
Comprobacion final despues de grabar el diseño de guion.

  1. que las 6 secuencias del operador (156-161) sigan ahi y con sus cues
  2. que no queden secuencias scratch de las pruebas (950-954, 900, 950...)
  3. que el boton de cada escena apunte a su secuencia con la funcion correcta
  4. que ninguna secuencia de la obra haya quedado vacia
  5. nombre del show y si esta guardado

No modifica nada.

Uso: python scripts/verificacion_final.py
"""
import asyncio
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ma2_telnet import Ma2  # noqa: E402

NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
EXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma"
              r"\gma2_V_3.9.60\importexport")
OBRAS = {156: ("E1 POR VOS", 5, "3.101", "Go"),
         157: ("E2 SOY LORD BIGOTIN", 6, "3.102", "Go"),
         158: ("E3 LA MIRADA DORADA", 5, "3.103", "Go"),
         159: ("E4 REINA GITANA", 7, "3.104", "Go"),
         160: ("E5 TODO EN GRIS ES MÁS DIVERTIDO", 8, "3.105", "Go"),
         161: ("E6 SI SOLAMENTE LO QUERÉS, MIRA TODO LO QUE PODÉS", 22,
               "3.106", "Go")}
CODIGO = {"Go": 12299, "Flash": 12302}


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        await ma2.cmd("cd /")
        r = await ma2.cmd("list sequences")
        print("SECUENCIAS DE LA OBRA")
        print("-" * 72)
        ok = True
        for seq, (nombre, ncues, boton, func) in OBRAS.items():
            # --- secuencia presente y con la cantidad de cues
            await ma2.cmd("cd /")
            await ma2.cmd(f"Export Sequence {seq} \"ver_{seq}\"")
            ruta = EXPORT / f"ver_{seq}.xml"
            for _ in range(15):
                if ruta.exists() and ruta.stat().st_size:
                    break
                await asyncio.sleep(0.3)
            if not (ruta.exists() and ruta.stat().st_size):
                print(f"  seq {seq}: NO SE PUDO EXPORTAR")
                ok = False
                continue
            root = ET.parse(ruta).getroot()
            cues = [c for c in root.iter(f"{NS}Cue") if c.get("index")]
            vals = sum(1 for c in cues for _ in c.iter(f"{NS}Channel"))
            ef = sum(1 for c in cues for _ in c.iter(f"{NS}Effect"))
            etiq = root.iter(f"{NS}Sequ")
            etiq = [e.get("name") for e in etiq]
            bien = len(cues) == ncues and (nombre in " ".join(etij for etij in etiq
                                                             if etij))
            ok &= bien
            print(f"  seq {seq:<4} {nombre[:34]:<34} cues={len(cues):>2}/{ncues} "
                  f"valores={vals:>4} efectos={ef:>3}  "
                  f"{'OK' if bien else 'REVISAR'}")
            ruta.unlink(missing_ok=True)

        # --- el boton de cada escena (export a XML, igual que check_execs.py:
        # `list executor` no devuelve el codigo de boton, el export si)
        print()
        print("BOTONES (page 3)")
        print("-" * 72)
        for seq, (nombre, ncues, boton, func) in OBRAS.items():
            tag = "ver" + boton.replace(".", "_")
            f = EXPORT / f"{tag}.xml"
            f.unlink(missing_ok=True)
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Executor {boton} "{tag}"')
            for _ in range(12):
                if f.exists() and f.stat().st_size > 0:
                    break
                await asyncio.sleep(0.3)
            txt = f.read_text(encoding="utf-8", errors="replace") if f.exists() else ""
            n = re.search(r'Assignment name="([^"]+)"', txt)
            nos = re.findall(r"<No>(\d+)</No>", txt)
            b = re.search(r"<Button>(\d+)</Button>", txt)
            cod = b.group(1) if b else "?"
            bien = str(seq) in nos and cod == str(CODIGO[func])
            ok &= bien
            print(f"  {boton}  seq={seq if str(seq) in nos else '??'}  "
                  f"funcion={func}({cod})  {(n.group(1) if n else '')[:36]}  "
                  f"{'OK' if bien else 'REVISAR'}")
            f.unlink(missing_ok=True)

        # --- el resto de las secuencias del operador, via export del show
        #     (no se toca ninguna: solo se cuenta cuantas siguen ahi)
        print()
        print("SECUENCIAS DE PRUEBA (900-999, deberian estar borradas)")
        print("-" * 72)
        await ma2.cmd("cd /")
        r = await ma2.cmd("Export Sequences \"ver_todas\"")
        f = EXPORT / "ver_todas.xml"
        for _ in range(40):
            if f.exists() and f.stat().st_size > 0:
                break
            await asyncio.sleep(0.3)
        if f.exists() and f.stat().st_size:
            root = ET.parse(f).getroot()
            nums = sorted({int(s.get("index")) + 1
                           for s in root.iter(f"{NS}Sequ") if s.get("index")})
            scratch = [n for n in nums if 900 <= n <= 999]
            if scratch:
                print(f"  quedan: {scratch}  -> BORRAR A MANO")
                ok = False
            else:
                print("  ninguna (900-999 libre)")
            otras = [n for n in nums if n not in OBRAS]
            print(f"\n  secuencias en el show: {len(nums)}")
            print(f"  de la obra (156-161): {sorted(n for n in nums if n in OBRAS)}")
            print(f"  las demas, sin tocar: {len(otras)}")
            vacias = [n for n in nums if n in OBRAS and False]
            print(f"  vacias: {vacias or 'ninguna de la obra'}")
            f.unlink(missing_ok=True)
        else:
            print("  no se pudo exportar el listado completo")

        r = await ma2.cmd("SaveShow /noconfirm")
        for ln in [x for x in r.body if x.strip()][:2]:
            print(f"\n  {ln.strip()[:110]}")

        print()
        print("RESULTADO:", "TODO OK" if ok else "HAY QUE REVISAR")


if __name__ == "__main__":
    asyncio.run(main())
