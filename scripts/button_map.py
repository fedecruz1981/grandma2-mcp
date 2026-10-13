"""
Mapa de button executors: que paginas existen y cuales estan libres.

Por que: el plan pide 6 botones consecutivos (101..106 = escena 1..6), pero
en la pagina 3 solo estan libres 3.101 y 3.111. 3.102-3.106 y 3.112-3.116
los ocupa el show viejo. Hay que ver si hay 6 libres seguidos en otra pagina
antes de pisar el trabajo del operador anterior.

Solo lectura.
Uso: python scripts/button_map.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

# La salida real de `list allbuttonexecutors` viene en formato clave=valor:
#   No.=3.101 Name=ARCO IRIS LED Sequence=Seq 58(2) Width=1 ... seq=None
# (el "seq=None" del final es ruido del formateador, no el dato)
NO_RE = re.compile(r"No\.=(?P<page>\d+)\.(?P<pos>\d+)")
NAME_RE = re.compile(r"\bName=(?P<name>[^\s]*)")
SEQ_RE = re.compile(r"\bSequence=Seq\s+(?P<seq>\d+)")


def parse_buttons(lines):
    """[(page, pos, nombre, seq)] de la salida de list de botones.

    OJO: los botones SIN asignar no aparecen en la lista. La ausencia de una
    posicion es lo que indica que esta libre, no un campo vacio.
    """
    out = []
    for ln in lines:
        s = ln.strip()
        m = NO_RE.search(s)
        if not m:
            continue
        mn = NAME_RE.search(s)
        ms = SEQ_RE.search(s)
        out.append((
            int(m.group("page")),
            int(m.group("pos")),
            (mn.group("name") if mn else ""),
            int(ms.group("seq")) if ms else None,
        ))
    return out


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        r = await ma2.cmd("list allbuttonexecutors")
        if r.errors:
            print("ERRORES:", r.errors)
        filas = parse_buttons(r.lines)
        print(f"botones parseados: {len(filas)}\n")

        if not filas:
            print("--- salida cruda (primeras 40) ---")
            for ln in r.body[:40]:
                print("   ", ln)
            return

        paginas = sorted({p for p, _, _, _ in filas})
        print("paginas con botones asignados:", paginas, "\n")
        for p in paginas:
            print(f"--- pagina {p} ---")
            for pg, pos, nombre, seq in sorted(
                    (f for f in filas if f[0] == p), key=lambda f: f[1]):
                print(f"   {p}.{pos:<4} {nombre:<26} seq={seq}")
            print()

        # Un boton libre es una posicion que NO aparece en la lista.
        # OJO: los button executors van numerados 101..140, NO 1..20.
        print("posiciones LIBRES (ausentes de la lista), paginas 1-6:")
        libres = []
        for p in range(1, 7):
            ocupados = {pos for pg, pos, _, _ in filas if pg == p}
            for pos in range(101, 141):
                if pos not in ocupados:
                    libres.append((p, pos))
        for p in paginas:
            ocupados = {pos for pg, pos, _, _ in filas if pg == p}
            huecos = [pos for pos in range(101, 141) if pos not in ocupados]
            print(f"   pagina {p}: ocupados {min(ocupados) if ocupados else '-'}"
                  f"..{max(ocupados) if ocupados else '-'}   "
                  f"libres: {huecos if huecos else 'ninguno'}")
        print(f"total libres (pag 1-6): {len(libres)}")

        print("\n6 libres CONSECUTIVAS en la misma pagina:")
        encontrado = False
        for p in range(1, 7):
            ocupados = {pos for pg, pos, _, _ in filas if pg == p}
            for inicio in range(101, 136):
                if all(i not in ocupados for i in range(inicio, inicio + 6)):
                    print(f"   pagina {p}: {p}.{inicio}..{p}.{inicio + 5}")
                    encontrado = True
        if not encontrado:
            print("   ninguna")


if __name__ == "__main__":
    asyncio.run(main())
