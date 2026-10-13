"""
PRUEBA DECISIVA:能否 crear la secuencia 156 y guardar un cue, verificado por
export.

Cadena de pruebas (la primera vez que se escribe algo en la consola):
  1. navegar a la capa 4
  2. seleccionar los 8 Protones (BF) con la sintaxis de unidad `23.1 Thru 30.1`
  3. setear COLORRGB1/2/3 y DIM
  4. `Store Cue 1 Sequence 156 /noconfirm`  <-- ACA ESTA LA INCERTIDUMBRE:
     la secuencia 156 no existe y en MA2 no hay verbo `Create`. Si Store la
     crea solos, tenemos el camino resuelto.
  5. `Export Sequence 156` y leer el XML, que es la unica verificacion real.

Valores usados = los de la Escena 1 Q1 (BF): Naranja 255,120,0 al 70%
  COLORRGB1 (R) = 100   -> 40 de prueba
  COLORRGB2 (G) = 47
  COLORRGB3 (B) = 0
  DIM          = 70
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

PASOS = [
    "cd LiveSetup Layers 4",
    "Fixture 23.1 Thru 30.1",
    'Attribute "ColorRGB1" At 100',
    'Attribute "ColorRGB2" At 47',
    'Attribute "ColorRGB3" At 0',
    "At 70",
    "Store Cue 1 Sequence 156 /noconfirm",
    "cd Sequences",
    "list",
    'Export Sequence 156 "test156"',
]


async def main():
    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()!r}\n")
        for c in PASOS:
            r = await ma2.cmd(c)
            print("=" * 78)
            print(f">>> {c}")
            print(f"    prompt : {r.prompt!r}")
            print(f"    errores: {r.errors if r.errors else 'ninguno'}")
            for ln in [x for x in r.body if x.strip()][:12]:
                print(f"      {ln[:160]}")


if __name__ == "__main__":
    asyncio.run(main())
