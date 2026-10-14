"""¿Dónde están los valores de un cue? Exploración del árbol cd.

`cd Sequence 156 Cue 1` + `list` devolvió "Cue 0 Cue 1" con todo en cero, que no
es lo que el XML exportado dice para ese cue. El `cd` sí aterriza bien (el prompt
lo confirma); lo que pasa es que `list` sobre un cue devuelve su ficha —nombre,
delay, fade, snap— y no su contenido. Ningún comando telnet devuelve los valores:
solo el export XML los tiene. Ver doc/CUE-READS-ES.md §10.2.

La sección 5 compara contra el XML exportado, que es la única fuente real.

Solo lectura: envía `list`, `info` y navega el árbol cd. No escribe en el show.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

SEQ = 156


async def main():
    c = Ma2()
    await c.connect()

    print("=" * 74)
    print("1 â€” Â¿DÃ“NDE ESTOY REALMENTE? (el prompt manda)")
    print("=" * 74)
    for cmd in (
        "cd /",
        f"cd Sequence {SEQ}",
        f"cd Sequence {SEQ} Cue 1",
        "cd /",
    ):
        r = await c.cmd(cmd)
        print(f"  {cmd:<32} prompt = {r.prompt!r}")

    print()
    print("=" * 74)
    print("2 â€” Â¿QUÃ‰ HAY BAJO EL CUE? (list de los hijos)")
    print("=" * 74)
    await c.cmd(f"cd Sequence {SEQ} Cue 1")
    for cmd in ("list", "cd /", f"cd Sequence {SEQ} Cue 1"):
        r = await c.cmd(cmd)
        print(f"\n  >>> {cmd}  (prompt {r.prompt!r})")
        for ln in r.body[:12]:
            print(f"      {ln.rstrip()[:120]}")

    print()
    print("=" * 74)
    print("3 â€” Â¿'list' recursivo? probemos dentro de los fixtures")
    print("=" * 74)
    await c.cmd("cd /")
    for ruta in (
        "cd Fixture 1",
        "list",
        "cd /",
        "cd Sequence 156 Cue 1 Fixture 1",
        "list",
        "cd /",
    ):
        r = await c.cmd(ruta)
        print(f"\n  >>> {ruta}  (prompt {r.prompt!r})")
        for ln in r.body[:8]:
            print(f"      {ln.rstrip()[:120]}")

    print()
    print("=" * 74)
    print("4 â€” Â¿Y con la secuencia en un executor? (Store a executor 1)")
    print("=" * 74)
    print("  NO se hace: store es destructivo sobre el show.", flush=True)
    print("  Lo que sÃ­ es seguro: ver quÃ© trae el export XML.", flush=True)

    print()
    print("=" * 74)
    print("5 â€” Â¿quÃ© dice el XML exportado del cue 1 de la 156?")
    print("=" * 74)
    ie = Path(r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport")
    chk = ie / "chk_156.xml"
    gen = ie / "build_156.xml"
    for f in (chk, gen):
        if not f.exists():
            print(f"  {f.name}: no existe")
            continue
        txt = f.read_text(encoding="utf-8", errors="replace")
        print(f"\n  --- {f.name} ({len(txt)} chars) ---")
        # primer cue completo
        ini = txt.find("<Cue ")
        if ini == -1:
            ini = txt.find("<Cue>")
        if ini == -1:
            print("    (no encontre una etiqueta de cue)")
            continue
        fin = txt.find("</Cue>", ini)
        trozo = txt[ini:fin + 7] if fin != -1 else txt[ini:ini + 2500]
        print(f"    primer cue: {len(trozo)} chars")
        for ln in trozo.splitlines()[:28]:
            print(f"      {ln.rstrip()[:118]}")

    await c.close()
    print("\n  (cd en /)")


asyncio.run(main())
