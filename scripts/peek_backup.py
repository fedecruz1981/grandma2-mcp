r"""
Mira el backup para entender como estaba el boton HUMO original (3.106).

Descomprime el show previo y guarda el contexto de "HUMO" y de las
definiciones de executor de la Page 3, para ver si el boton tenia ajustes
especiales (toggle, flash, fader) que un Assign simple no recupera.

El resultado va a data/backup_humo_contexto.txt (no a stdout, para evitar el
error de cp1252 con bytes binarios).

Uso: python scripts\peek_backup.py
"""
import gzip
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
p = sorted(DATA.glob("backup_*.show.gz"))[-1]
raw = gzip.open(p, "rb").read()

print(f"{p.name}: {len(raw)} bytes")
print("primeros 120 bytes:", raw[:120])

salida = []
for pat in (b"HUMO", b"humo", b"Page 3", b"3.106"):
    hits = list(re.finditer(pat, raw))
    salida.append(f"\n\n########## {pat!r}: {len(hits)} hits\n")
    for m in hits[:10]:
        s, e = max(0, m.start() - 350), min(len(raw), m.end() + 350)
        salida.append(f"\n--- @ {m.start()}\n")
        salida.append(raw[s:e].decode("utf-8", "replace"))

(DATA / "backup_humo_contexto.txt").write_text("".join(salida),
                                              encoding="utf-8")
print(f"escrito data/backup_humo_contexto.txt ({len(salida)} bloques)")
