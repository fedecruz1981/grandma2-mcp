"""¿El `.0` de un número de cue rompe el comando?

Compara byte a byte el mismo cue escrito de las dos formas, en una secuencia
donde ese cue existe. Antes de esto solo se comparaba el largo de la respuesta,
que no distingue nada.

Respuesta (3.9.60.82, show "inti y luna oct2026"): los 2 caracteres de
diferencia están solo en la línea del eco; el cuerpo de datos es idéntico. La
consola normaliza `1.0` a `1`. Ver doc/CUE-READS-ES.md §10.1.

Solo lectura: envía `list` y navega el árbol cd, no escribe nada en el show.
"""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402


def cue_ids(resp):
    out = []
    for ln in resp.body:
        m = re.match(r"^\s*Cue\s+(\d+(?:\.\d+)?)\b", ln.strip())
        if m:
            out.append(m.group(1))
    return out


def seq_ids(resp):
    out = []
    for ln in resp.body:
        m = re.match(r"^\s*Sequ\s+(\d+)\s", ln.strip())
        if m:
            out.append(int(m.group(1)))
    return out


async def main():
    c = Ma2()
    await c.connect()
    print("conectado", flush=True)

    print("escaneando secuencias con >=3 cues...", flush=True)
    r = await c.cmd("list sequence")
    seqs = seq_ids(r)
    print(f"  {len(seqs)} secuencias en el show", flush=True)

    buenas = []
    for sid in seqs:
        rr = await c.cmd(f"list cue sequence {sid}")
        ids = cue_ids(rr)
        if len(ids) >= 3:
            buenas.append((len(ids), sid))
            if len(buenas) >= 3:
                break
        if sid % 40 == 0:
            print(f"  ...idas {sid}", flush=True)

    if not buenas:
        print("ninguna secuencia con 3+ cues", flush=True)
        await c.close()
        return

    buenas.sort(reverse=True)
    n, seq = buenas[0]
    print(f"\nusando sequence {seq} con {n} cues", flush=True)

    r = await c.cmd(f"list cue sequence {seq}")
    ids = cue_ids(r)
    print(f"cues: {ids}", flush=True)

    print("\n=== EL '.0' ROMPE EL COMANDO? ===", flush=True)
    iguales_todos = True
    for cue in ids:
        a = await c.cmd(f"list cue {cue} sequence {seq}")
        b = await c.cmd(f"list cue {cue}.0 sequence {seq}")
        igual = a.raw == b.raw
        iguales_todos = iguales_todos and igual
        va = "VACIO" if "NO OBJECTS" in a.raw.upper() else f"{len(a.body)} lin"
        vb = "VACIO" if "NO OBJECTS" in b.raw.upper() else f"{len(b.body)} lin"
        print(f"  cue {cue:<5} -> {va:<8} | cue {cue}.0 -> {vb:<8} | identicas: {igual}", flush=True)

    print(f"\n>> el '.0' cambia algo: {not iguales_todos}", flush=True)

    print("\n=== QUE TRAE 'list cue' ===", flush=True)
    for cue in ids[:2]:
        rr = await c.cmd(f"list cue {cue} sequence {seq}")
        print(f"\n  list cue {cue} sequence {seq} ({len(rr.body)} lineas):", flush=True)
        for ln in rr.body:
            print(f"    {ln.rstrip()[:140]}", flush=True)

    print("\n=== QUE TRAE cd AL CUE + list ===", flush=True)
    for cue in ids[:2]:
        await c.cmd(f"cd Sequence {seq} Cue {cue}")
        rr = await c.cmd("list")
        print(f"\n  cd Sequence {seq} Cue {cue} + list ({len(rr.body)} lineas):", flush=True)
        for ln in rr.body:
            print(f"    {ln.rstrip()[:140]}", flush=True)
        await c.cmd("cd /")

    await c.close()
    print("\ncd en /", flush=True)


asyncio.run(main())
