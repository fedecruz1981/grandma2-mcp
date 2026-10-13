"""
Asigna la secuencia grabada al boton 101 del executor y guarda el show.

Por que: la Escena 1 quedo grabada en la SECUENCIA 156 del pool, pero sin
asignar a ningun boton. El operador sigue viendo el contenido viejo (con
arcoiris) en el boton 101 porque no se habia tocado ese executor.

Pasos, con la respuesta cruda de la consola en cada paso:
  1. Ver que hay AHORA en los botones 3.101..3.106 (estado previo, por si
     hay que volver atras)
  2. Asignar la secuencia 156 al boton 3.101
  3. Releer el boton para confirmar
  4. SaveShow

Sintaxis: `cd Executor <pagina>.<boton>` es la que funciona (singular;
`cd Executors` da OBJECT DOES NOT EXIST).

Uso: python scripts\asignar_boton.py <secuencia> <pagina> <boton>
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402


async def cmd_verbose(ma2, c, ver_cuerpo=8):
    r = await ma2.cmd(c)
    print(f">>> {c}")
    print(f"    {'ok' if not r.errors else 'ERR ' + str(r.errors)}")
    for ln in [x for x in r.body if x.strip()][:ver_cuerpo]:
        print(f"      {ln.strip()[:150]}")
    return r


async def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return
    secuencia = int(sys.argv[1])
    pagina = int(sys.argv[2])
    boton = int(sys.argv[3])

    async with Ma2() as ma2:
        print(f"prompt: {await ma2.at_prompt()!r}\n")

        print("#" * 78)
        print("# 1) ESTADO PREVIO de los botones de esta pagina")
        for b in range(101, 107):
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"cd Executor {pagina}.{b}")
            if r.errors:
                print(f"  {pagina}.{b}: (libre)")
                continue
            lst = await ma2.cmd("list")
            vals = [x.strip() for x in lst.body if x.strip()][:4]
            print(f"  {pagina}.{b}: prompt={r.prompt!r}")
            for v in vals:
                print(f"        {v[:140]}")

        print()
        print("#" * 78)
        print(f"# 2) ASIGNAR secuencia {secuencia} al boton {pagina}.{boton}")
        await ma2.cmd("cd /")
        await cmd_verbose(ma2, f"cd Executor {pagina}.{boton}")
        await cmd_verbose(ma2, f"Assign Sequence {secuencia}")

        print()
        print("#" * 78)
        print("# 3) VERIFICAR el boton")
        await ma2.cmd("cd /")
        await cmd_verbose(ma2, f"cd Executor {pagina}.{boton}")
        r = await cmd_verbose(ma2, "list")

        print()
        print("#" * 78)
        print("# 4) GUARDAR el show")
        await ma2.cmd("cd /")
        await cmd_verbose(ma2, "SaveShow /noconfirm")


if __name__ == "__main__":
    asyncio.run(main())