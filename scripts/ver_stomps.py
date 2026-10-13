r"""
Verifica que los STOMP quedaron grabados en la consola.

Que es un stomp: cuando un cue deja un efecto corriendo (ej. ef7 RGB Rainbow
sobre el COLORRGB de los LED) y el cue siguiente escribe un color fijo sobre ese
mismo atributo, sin pisar el efecto este sigue corriendo por encima: el efecto
de cambio de color queda "colgado" y los LED nunca se quedan con el color del
cue. En la consola eso se resuelve con el macro 6 "Stomp running Effects"
(ClearSelection + Stomp PresetType Thru).

Como se guarda: NO es un atributo `stomp` en el XML (se probaron cuatro
grafias y la consola las descarto). Es
`<EffectFlags form_index="0" sub_form_index="0" />` en el CueData del valor, sin
ningun <Effect> al lado. Averiguado en scripts/probar_stomp_en_secuencia.py.

Este script exporta cada secuencia de la obra, cuenta los stomps que hay
realmente y los compara con los que el plan dice que deberian ir.

Uso: python scripts\ver_stomps.py
"""
import asyncio
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_sequences as B  # noqa: E402
from ma2_telnet import Ma2  # noqa: E402
from ma2_telnet import ANSI  # noqa: E402

EXPORT_DIR = B.EXPORT_DIR
NS = "{http://schemas.malighting.de/grandma2/xml/MA}"
PLAN = B.DATA / "plan.json"


def esperados():
    """{num_secuencia: {cue: n_stomps}} desde el plan, sin tocar la consola."""
    import json
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    escenas = sorted({c["scene"] for c in plan}, key=lambda s: int(s.split()[1]))
    out = {}
    for i, esc in enumerate(escenas, 1):
        ce = frozenset()
        por_cue = {}
        for j, c in enumerate([c for c in plan if c["scene"] == esc], 1):
            ents = B.entradas_de_cue(c, ce)
            ce = B.entradas_de_cue.ultimo_con_efecto
            n = sum(1 for e in ents if len(e) > 4 and e[4])
            if n:
                por_cue[j] = n
        out[B.SEQ_BASE + i] = por_cue
    return out


async def exportar(ma2, seq, sello):
    tag = f"stv_{seq}_{sello}"
    f = EXPORT_DIR / f"{tag}.xml"
    f.unlink(missing_ok=True)
    await ma2.drain()
    await ma2._raw(f'Export Sequence {seq} "{tag}"')
    buf = await ma2._read_until_prompt(max_wait=6.0)
    if "Overwrite" in ANSI.sub("", buf or ""):
        await ma2.drain()
        await ma2._raw("2")
        await ma2._read_until_prompt(max_wait=3.0)
    for _ in range(25):
        if f.exists() and f.stat().st_size > 0:
            break
        await asyncio.sleep(0.3)
    if not (f.exists() and f.stat().st_size > 0):
        return None
    root = ET.parse(f).getroot()
    f.unlink(missing_ok=True)
    return root


def leidos(root):
    """{cue: n_stomps} leidos del export real de la consola."""
    out = {}
    for cue in root.iter(f"{NS}Cue"):
        idx = cue.get("index")
        if idx is None:
            continue
        n = 0
        for cd in cue.iter(f"{NS}CueData"):
            ef = cd.find(f"{NS}Effect")
            if ef is not None:
                continue                      # tiene efecto: no es stomp
            fl = cd.find(f"{NS}EffectFlags")
            if fl is not None and fl.get("form_index") == "0" \
                    and fl.get("sub_form_index") == "0":
                n += 1
        if n:
            out[int(idx)] = n
    return out


async def main():
    sello = int(time.time()) % 100000
    esp = esperados()
    total_esp = sum(sum(v.values()) for v in esp.values())
    print(f"host: {os.environ.get('GMA_HOST', '(default 192.168.0.71)')}")
    print(f"el plan pide {total_esp} stomps en total")

    fallos, total_real = [], 0
    async with Ma2() as ma2:
        for seq in sorted(esp):
            root = await exportar(ma2, seq, sello)
            if root is None:
                print(f"\n  seq {seq}: no se pudo exportar")
                fallos.append(f"seq {seq}: sin export")
                continue
            leido = leidos(root)
            real = sum(leido.values())
            total_real += real
            falta = {k: v for k, v in esp[seq].items() if leido.get(k, 0) != v}
            marca = "OK" if not falta else "DIFIERE"
            print(f"\n  seq {seq}: {len(leido)} cues con stomp, {real} stomps  "
                  f"[{marca}]")
            for cue in sorted(esp[seq]):
                e, l = esp[seq][cue], leido.get(cue, 0)
                if e or l:
                    print(f"      cue {cue:>2}: esperado={e:>3}  en consola={l:>3}"
                          + ("   <-- NO CUADRA" if e != l else ""))
            for cue, n in falta.items():
                fallos.append(f"seq {seq} cue {cue}: esperado {esp[seq][cue]}, "
                              f"hay {leido.get(cue, 0)}")
        await ma2.drain()
        await ma2._raw("Clear")
        await ma2._read_until_prompt(max_wait=3.0)

    print()
    print("=" * 74)
    print(f"esperados={total_esp}  en la consola={total_real}")
    if fallos:
        print(f"HAY {len(fallos)} PROBLEMAS:")
        for f in fallos[:25]:
            print(f"   - {f}")
        return 1
    print("TODO OK: cada stomp del plan esta grabado en la consola.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))