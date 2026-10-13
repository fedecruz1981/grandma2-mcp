"""
Prueba systematicallyo las rutas documentadas de `List` para leer un cue.

Del foro de MA Lighting: los numeros de `List` dependen del prompt actual.
"List 1" en EditSetup = DMX_Profiles, pero en [Fixture] = Showfile.
Por eso "list color" puede fallar aunque el objeto exista.

Este script prueba la matriz completa de comandos sobre un cue y reporta
cuales funcionan, para descubrir la sintaxis correcta por medicion.

Uso: python scripts/probe_routes.py [seq] [cue]
"""
import asyncio
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])

from ma2_telnet import Ma2


# Rutas candidatas para leer el contenido de un cue.
# (etiqueta, comando)
ROUTES = [
    # dentro del cue
    ("list preset",              "list preset"),
    ("list preset 1",            "list preset 1"),
    ("list dimmer",              "list dimmer"),
    ("list dimmer preset",       "list dimmer preset"),
    ("list position",            "list position"),
    ("list pos",                 "list pos"),
    ("list color",               "list color"),
    ("list colorpreset",         "list colorpreset"),
    ("list beam",                "list beam"),
    ("list gobo",                "list gobo"),
    ("list control",             "list control"),
    ("list attribute",           "list attribute"),
    ("list fixture",             "list fixture"),
    ("list channel",             "list channel"),
    ("list group",               "list group"),
    ("list appearance",          "list appearance"),
    ("list look",                "list look"),
    ("list value",               "list value"),
    # sobre el cue desde arriba
    ("list cue",                 "list cue"),
    ("list cue 1",               "list cue 1"),
    ("info cue",                 "info cue"),
    ("info cue 1",               "info cue 1"),
    # contexto de secuencia
    ("cd seq; list preset",      "__SEQ__"),
    ("cd seq; list cue",         "__SEQ__CUE"),
    # la forma documentada que usan los MCP
    ("list cue 1 sequence N",    "__SEQCUE__"),
]


async def probe(ma2: Ma2, seq: int, cue: int):
    print("=" * 78)
    print(f"  SEQ {seq} / CUE {cue}")
    print("=" * 78)

    nav = await ma2.cmd(f"cd Sequence {seq} Cue {cue}")
    print(f"  prompt: {nav.prompt}\n")

    results = {}
    for label, cmd in ROUTES:
        if cmd == "__SEQ__":
            await ma2.cmd(f"cd Sequence {seq}")
            r = await ma2.cmd("list preset")
            await ma2.cmd(f"cd Sequence {seq} Cue {cue}")
        elif cmd == "__SEQ__CUE":
            await ma2.cmd(f"cd Sequence {seq}")
            r = await ma2.cmd("list cue")
            await ma2.cmd(f"cd Sequence {seq} Cue {cue}")
        elif cmd == "__SEQCUE__":
            r = await ma2.cmd(f"list cue {cue} sequence {seq}")
        else:
            r = await ma2.cmd(cmd)

        body = [ln for ln in r.body if ln.strip()]
        has_content = bool(body) and not all(
            "NO OBJECTS FOUND" in ln.upper() for ln in body
        )
        status = "OK " if has_content and not r.errors else "ERR"
        results[label] = (status, body, r.errors)

        marker = ""
        if has_content:
            first = next((ln for ln in body if not ln.startswith(("No.", "Number"))), "")
            marker = f"  <- {first.strip()[:60]}"
        print(f"  [{status}] {label:<26}{marker}")

        # si el prompt se movió, vuelve al cue
        if "Cue" not in r.prompt:
            await ma2.cmd(f"cd Sequence {seq} Cue {cue}")

    return results


async def main():
    seq = int(sys.argv[1]) if len(sys.argv) > 1 else 137
    cue = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    async with Ma2() as ma2:
        print("prompt:", repr(await ma2.at_prompt()), "\n")
        res = await probe(ma2, seq, cue)

        print("\n\n### RUTAS CON CONTENIDO ###")
        for label, (status, body, errs) in res.items():
            if status == "OK " and body:
                print(f"\n--- {label} ---")
                for ln in body[:25]:
                    print("   ", ln)


if __name__ == "__main__":
    asyncio.run(main())