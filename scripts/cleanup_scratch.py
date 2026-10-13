r"""
Limpia las secuencias de prueba (190-193) que quedaron de los tests.

Las secuencias reales del show son 156-161 (botones 3.101-3.106). Las 190-193
las usaron los scripts de prueba (xml_import_test, merge_test, pt_capture,
effect_test*). No tienen executor asignado; se borran para no dejar basura.

Se manda cada Delete por separado (encadenar con ; o && falla en esta consola).

Uso: python scripts\cleanup_scratch.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

PRUEBA = [190, 191, 192, 193]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for seq in PRUEBA:
            await ma2.cmd("cd /")
            p = await ma2.cmd(f"cd Sequence {seq}")
            existe = "Sequ" in (p.prompt or "")
            nombre = (p.prompt or "").split("/")[-1] if existe else "-"
            if not existe:
                print(f"  seq {seq}: no existe")
                continue
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"Delete Sequence {seq}")
            estado = "borrada" if not r.errors else f"ERROR {r.errors}"
            print(f"  seq {seq}: {nombre!r} -> {estado}")
        # confirmar que las reales siguen
        print("  reales:")
        for seq in range(156, 162):
            await ma2.cmd("cd /")
            p = await ma2.cmd(f"cd Sequence {seq}")
            print(f"    {seq}: {p.prompt!r}")


if __name__ == "__main__":
    asyncio.run(main())
