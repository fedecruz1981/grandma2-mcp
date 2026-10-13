"""
Runner VERBOSE: muestra cada byte que se manda a la consola y la respuesta
cruda completa, sin filtrar nada.

Sirve para que veas exactamente que le estoy mandando a la consola y que
me contesta, byte por byte, en vez de una linea resumida.

Muestra por cada comando:
  [hora]   momento en que se envio
  ENVIO    los bytes exactos que van por el socket (\\r\\n visible)
  RESPUESTA  todo lo que vuelve, crudo, incluyendo el prompt
  MS       cuanto tardo la consola

Uso:
  python scripts/ma2_verbose.py "list /?"
  python scripts/ma2_verbose.py "cd Fixture 15" "list dmx"
  python scripts/ma2_verbose.py --slow "cd Fixture 15"   # 2s entre comandos
"""
import asyncio
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from ma2_telnet import Ma2

DIM = "\033[2m"
CYAN = "\033[36m"
YEL = "\033[33m"
GRN = "\033[32m"
RED = "\033[31m"
RST = "\033[0m"


def stamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def show_raw(label, raw, color):
    """Imprime la respuesta cruda linea por linea, sin reinterpretar."""
    print(f"  {DIM}{label}{RST}")
    if not raw:
        print(f"    {DIM}(vacio){RST}")
        return
    for ln in raw.splitlines():
        # marcar errores de color distinto para que salten a la vista
        if "Error" in ln:
            print(f"    {RED}{ln}{RST}")
        else:
            print(f"    {color}{ln}{RST}")


async def main():
    args = sys.argv[1:]
    slow = False
    if args and args[0] == "--slow":
        slow = True
        args = args[1:]
    if not args:
        print(__doc__)
        return

    async with Ma2() as ma2:
        prompt_inicial = await ma2.at_prompt()
        print(f"{DIM}conectado. prompt inicial:{RST}")
        print(f"    {CYAN}{prompt_inicial}{RST}\n")
        print(f"{DIM}{'=' * 74}{RST}")

        for c in args:
            print(f"\n{CYAN}[{stamp()}]{RST} {YEL}>>>{RST} {c}")
            payload = c + "\r\n"
            print(f"  {DIM}ENVIO ({len(payload)} bytes, CR+LF al final){RST}")

            t0 = time.perf_counter()
            r = await ma2.cmd(c)
            ms = (time.perf_counter() - t0) * 1000

            print(f"  {DIM}--- respuesta cruda ---{RST}")
            show_raw("recibido", r.raw, GRN)

            ok = "Error" not in r.raw
            flag = f"{GRN}OK{RST}" if ok else f"{RED}FALLO{RST}"
            print(f"  {DIM}fin en {ms:.0f} ms  ->{RST} {flag}")
            print(f"  {DIM}prompt final: {r.prompt}{RST}")

            if slow:
                await asyncio.sleep(2)

        print(f"\n{DIM}{'=' * 74}{RST}")
        print(f"{DIM}listo. {len(args)} comando(s). nada se escribio en la consola.{RST}")


if __name__ == "__main__":
    asyncio.run(main())