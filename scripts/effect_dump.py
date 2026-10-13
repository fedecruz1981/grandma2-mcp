"""
Explora el pool de effects: numeros, nombres y parametros.

Por que: el operador decidio que los multicolor y los flash se graben con
effect asignado. Hay 28 cues con effect y 15 con multicolor, asi que esto
debe estar confirmado ANTES de escribir, no improvisado sobre el show.

`Assign Effect` necesita saber cuantos parametros espera cada effect y de que
tipo, asi que el listado tiene que incluir el bloque de parametros.

Solo lectura. Escribe data/_effects.txt.
Uso: python scripts/effect_dump.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

PRUEBAS = [
    "list effectlibrary",
    "list effect",
    "cd Effect 1",
    "list",
]


async def main():
    out = []
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for c in PRUEBAS:
            await ma2.cmd("cd /")
            r = await ma2.cmd(c)
            out.append("=" * 78)
            out.append(f">>> {c}")
            out.append(f"    prompt: {r.prompt!r}")
            if r.errors:
                out.append(f"    ERRORES: {r.errors}")
            vacias = 0
            for ln in r.body:
                if ln.strip():
                    out.append(f"    {ln.rstrip()[:170]}")
                    vacias += 1
                if vacias > 90:
                    out.append("    ... (truncado)")
                    break
            if not vacias:
                out.append("    (vacio)")
            out.append("")

    Path("data/_effects.txt").write_text("\n".join(out), encoding="utf-8")
    print("escrito data/_effects.txt")


if __name__ == "__main__":
    asyncio.run(main())