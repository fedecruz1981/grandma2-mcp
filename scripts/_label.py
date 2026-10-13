import asyncio, sys
sys.path.insert(0, "scripts")
from ma2_telnet import Ma2

async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for c in ['Label Sequence 156 "E1 POR VOS"',
                  "cd /",
                  "cd Executor 3.101",
                  "list"]:
            r = await ma2.cmd(c)
            print(f">>> {c}")
            print(f"    {'ok' if not r.errors else 'ERR ' + str(r.errors)}")
            for ln in [x for x in r.body if x.strip()][:6]:
                print(f"      {ln.strip()[:150]}")
        # releer el prompt del boton
        await ma2.cmd("cd /")
        r = await ma2.cmd("cd Executor 3.101")
        print(f"\nprompt del boton 3.101: {r.prompt!r}")
        await ma2.cmd("cd /")
        r = await ma2.cmd("cd Sequence 156")
        print(f"prompt de la secuencia : {r.prompt!r}")
        print()
        r = await ma2.cmd("SaveShow /noconfirm")
        print(f">>> SaveShow /noconfirm")
        for ln in [x for x in r.body if x.strip()][:4]:
            print(f"      {ln.strip()[:150]}")
asyncio.run(main())
