r"""
Busca "HUMO" dentro del backup del show (antes de tocar nada).

data/backup_fede_inti_luna_2026-09-30_1840.show.gz es el show guardado antes de
las modificaciones. Si HUMO era una secuencia, su nombre y contenido estan ahi.

Uso: python scripts\search_backup.py
"""
import gzip
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

cands = sorted(DATA.glob("backup_*.show.gz"))
print("backups:", [c.name for c in cands])
if not cands:
    raise SystemExit("no hay backup")
p = cands[-1]
raw = gzip.open(p, "rb").read()
print(f"{p.name}: {len(raw)} bytes descomprimidos")

for pat in (rb"HUMO", rb"Smoke", rb"smoke", rb"Haze", rb"haze"):
    hits = list(re.finditer(pat, raw, re.I))
    print(f"\n=== {pat!r}: {len(hits)} coincidencias")
    for m in hits[:8]:
        s = max(0, m.start() - 260)
        e = min(len(raw), m.end() + 260)
        txt = raw[s:e].decode("utf-8", "replace")
        txt = txt.replace("\r", " ").replace("\n", " ")
        print(f"  ...{txt}...")
        print("  ---")
