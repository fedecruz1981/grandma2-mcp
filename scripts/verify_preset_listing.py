"""
Test DECISIVO de si `list preset` en un cue lee el cue real o miente.

Secuencias que sabemos distintas por oficio:
  16  = LED FRENTE     (ejecutor 1.3, Protone LED, solo frente)
  45  = LAMPARA BEAM   (ejecutor 1.1, Beamer 250, 15ch, color+gobo)
  60  = nebula 162     (ejecutor 1.2, Nebula Max, 5ch)
  123 = MALVADO FEIDER
  137 = malvado
  142 = malvado

Si 16, 45 y 60 devuelven los MISMOS presets, `list preset` esta leyendo
otra cosa (seleccion del programador o pool global) y es inservible.
Si devuelven distintos, es real y puedo barrer las 155 secuencias.

Uso: python scripts/verify_preset_listing.py
"""
import asyncio
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])

from ma2_telnet import Ma2

TARGETS = [
    (16, "LED FRENTE"),
    (45, "LAMPARA BEAM"),
    (60, "nebula 162"),
    (123, "MALVADO FEIDER"),
    (137, "malvado"),
    (142, "malvado"),
]


async def read_cue(ma2, seq, cue=1):
    nav = await ma2.cmd(f"cd Sequence {seq} Cue {cue}")
    if "Cue" not in nav.prompt:
        return None, f"NO ENTRO: {nav.prompt!r}"
    r = await ma2.cmd("list preset")
    rows = [
        ln.strip() for ln in r.body
        if ln.strip() and not ln.strip().startswith(("No.", "Number"))
    ]
    return rows, None


async def main():
    async with Ma2() as ma2:
        results = {}
        for seq, known in TARGETS:
            rows, err = await read_cue(ma2, seq)
            results[seq] = (known, rows, err)
            print(f"\nSEQ {seq:<4} {known:<16} prompt={await ma2.at_prompt()!r}")
            if err:
                print(f"   !! {err}")
            elif not rows:
                print("   (sin presets)")
            else:
                for ln in rows:
                    print("   ", ln)

        # ---- veredicto ----
        print("\n" + "=" * 72)
        print("VEREDICTO")
        print("=" * 72)
        distinct = {}
        for seq, (known, rows, err) in results.items():
            if rows:
                distinct.setdefault(tuple(rows), []).append((seq, known))
        if len(distinct) == 1:
            print("FALLA: todas las secuencias devuelven la MISMA lista.")
            print("        `list preset` NO lee el cue. Inservible.")
        else:
            print(f"OK: {len(distinct)} listas distintas entre {len(results)} secuencias.")
            for rows, seqs in distinct.items():
                print(f"\n 共享 {len(rows)} preset(s) -> {[s for s, _ in seqs]}")
                for ln in rows:
                    print("      ", ln)


if __name__ == "__main__":
    asyncio.run(main())