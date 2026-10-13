r"""
Asigna las secuencias de las escenas a los botones 3.101-3.106 (Page 3)
y verifica leyendo el prompt de cada executor.

  seq 156 -> 3.101   (ya estaba de antes; se re-verifica)
  seq 157 -> 3.102   (COLORES PRIMARIOS)
  seq 158 -> 3.103   (malvado)
  seq 159 -> 3.104   (BANCO COLORIDA CONTRA)
  seq 160 -> 3.105   (BEAN ARCOIRIS)
  seq 161 -> 3.106   (HUMO)

`Assign Sequence N Executor P.B` reemplaza lo que hubiera en ese executor.
El unico read-back fiable es el prompt del executor (trae el nombre).

Uso: python scripts\assign_executors.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

MAPA = [
    (156, 3, 101),
    (157, 3, 102),
    (158, 3, 103),
    (159, 3, 104),
    (160, 3, 105),
    (161, 3, 106),
]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        ok = True
        for seq, page, btn in MAPA:
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"Assign Sequence {seq} Executor {page}.{btn}")
            if r.errors:
                print(f"  seq {seq} -> {page}.{btn}: ERROR {r.errors}")
                ok = False
            # read-back
            await ma2.cmd("cd /")
            p = await ma2.cmd(f"cd Executor {page}.{btn}")
            print(f"  seq {seq} -> {page}.{btn}   prompt={p.prompt!r}")
            for ln in [x for x in p.body if x.strip()][:2]:
                print(f"       {ln.strip()[:110]}")
        await ma2.cmd("cd /")
        r = await ma2.cmd("SaveShow /noconfirm")
        for ln in [x for x in r.body if x.strip()][:2]:
            print(f"\n  {ln.strip()}")
        if not ok:
            print("\n  OJO: hubo errores")


if __name__ == "__main__":
    asyncio.run(main())
