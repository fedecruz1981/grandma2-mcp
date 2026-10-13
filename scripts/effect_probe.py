"""
Explora el comando `Effect` de grandMA2 por telnet, en solo lectura.

Contexto: el cue sheet de "Inti y Luna" es effect-driven (chase, barrido,
parpadeo, strobo, rotacion de color). Los strobes/stomps NO existen como
comando, y antes se vio que `Effect` reportaba "No Options found". Falta
determinar si eso era "el comando existe pero no se puede listar sintaxis"
o "no se puede crear/asignar efectos por telnet".

SiEffects se pueden crear y asignar, el show se arma casi entero por telnet.
Si no, hay que hacer ~20 cues de efecto a mano en la consola.

NO ESCRIBE NADA: solo help/list/cd.
Uso: python scripts/effect_probe.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

PRUEBAS = [
    "help Effect",
    "Effect /?",
    "List Effect",
    "cd Effects",
    "List",
    "cd Effect 1",
    "List",
    "cd Sequences",
    "List Sequence 1",
    "help Assign",
    "help Set",
]


async def main():
    async with Ma2() as ma2:
        print(f"prompt inicial: {await ma2.at_prompt()}\n")
        for c in PRUEBAS:
            r = await ma2.cmd(c)
            print("=" * 78)
            print(f">>> {c}")
            print(f"    prompt: {r.prompt}")
            if r.errors:
                print(f"    ERRORES: {r.errors}")
            cuerpo = [ln for ln in r.body if ln.strip()]
            for ln in cuerpo[:22]:
                print(f"      {ln}")
            if len(cuerpo) > 22:
                print(f"      ... (+{len(cuerpo) - 22} lineas)")
            if not cuerpo and not r.errors:
                print("      (respuesta vacia)")


if __name__ == "__main__":
    asyncio.run(main())
