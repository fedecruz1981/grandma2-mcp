"""
Explora la estructura del preset 'dim frente' (Dimmer 1.1).

`cd Preset 1` entra directo al preset 1.1 (no al pool). `list` ahi no
devuelve nada. Hay que navegar a las sub-ramas del preset: fixture, group,
o los valores.

Del manual MA2: un preset tiene sub-objetos por tipo de dato. En la
consola se ven en el árbol Sequence/Cue/... y Preset/.../Values.

Este script prueba rutas de navegacion dentro del preset.
Uso: python scripts/explore_preset.py [preset_type] [slot]
"""
import asyncio
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])

from ma2_telnet import Ma2

SUBPATHS = [
    "",
    "Values",
    "Appearance",
    "Fixture",
    "Group",
    "Channel",
    "Attribute",
    "Presets",
    "Appearance/Dimmer",
    "Appearance/Position",
    "Appearance/Color",
    "Appearance/Beam",
    "Appearance/Gobo",
    "Appearance/Control",
]


async def main():
    ptype = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    slot = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    base = f"Preset {ptype}.{slot}"

    async with Ma2() as ma2:
        nav = await ma2.cmd(f"cd {base}")
        print(f"prompt: {nav.prompt}\n")

        for sub in SUBPATHS:
            target = f"{base} {sub}".strip() if sub else base
            r = await ma2.cmd(f"cd {target}")
            ok = "Error" not in r.raw
            marker = "  ok" if ok else "  --"
            print(f"[{marker}] cd {target:<38} -> {r.prompt}")

            if ok:
                lr = await ma2.cmd("list")
                body = [ln for ln in lr.body if ln.strip()]
                if body:
                    for ln in body[:15]:
                        print("        ", ln)
                else:
                    print("         (list vacio)")


if __name__ == "__main__":
    asyncio.run(main())