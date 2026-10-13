import asyncio, sys
from pathlib import Path
sys.path.insert(0, "scripts")
from ma2_telnet import Ma2

async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        print("--- prompts de los botones (el nombre es lo que cambia) ---")
        for b in range(101, 107):
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"cd Executor 3.{b}")
            print(f"  3.{b}: {r.prompt!r}")
        print()
        print("--- secuencia 156 ---")
        for s in (156, 157):
            await ma2.cmd("cd /")
            r = await ma2.cmd(f"cd Sequence {s}")
            print(f"  Sequence {s}: prompt={r.prompt!r} err={r.errors}")
asyncio.run(main())
