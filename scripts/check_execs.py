r"""
Chequea que los botones 3.101 (seq 156) y 3.103 (seq 158) sigan apuntando a
su secuencia y con la funcion correcta, exportando los executors a XML.

3.101 estuvo en Flash hasta el 2026-10-02. Se cambio a Go porque con la escena 1
completa (5 cues) en ese boton, Flash corria la escena entera sola y no se podia
detenerse en Q3 (interaccion con el publico) ni en Q4 (el congelamiento de Luna).
Ahora los seis botones de escena van en Go. Ver scripts/cambiar_101_go.py.

Uso: python scripts\check_execs.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
# boton -> (secuencia, funcion esperada)
BOTONES = {
    "3.101": ("156", "Go"),
    "3.102": ("157", "Go"),
    "3.103": ("158", "Go"),
    "3.104": ("159", "Go"),
    "3.105": ("160", "Go"),
    "3.106": ("161", "Go"),
}
# codigo <Button> de cada funcion
CODIGO = {"Go": "12299", "Temp": "12291", "On": "12293",
          "Off": "12290", "Flash": "12302", "Swop": "12306",
          "Toggle": "12307"}


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()
        for boton, (seq_esp, func_esp) in BOTONES.items():
            nombre = "exec" + boton.replace(".", "_")
            f = EXPORT_DIR / f"{nombre}.xml"
            if f.exists():
                f.unlink()
            await ma2.cmd("cd /")
            r = await ma2.cmd(f'Export Executor {boton} "{nombre}"')
            for _ in range(12):
                if f.exists() and f.stat().st_size > 0:
                    break
                await asyncio.sleep(0.3)
            txt = f.read_text(encoding="utf-8", errors="replace") if f.exists() else ""
            name = re.search(r'Assignment name="([^"]+)"', txt)
            seq = re.findall(r"<No>(\d+)</No>", txt)
            btn = re.search(r"<Button>(\d+)</Button>", txt)
            codigo = btn.group(1) if btn else "?"
            ok = codigo == CODIGO[func_esp] and seq_esp in seq
            print(f"  {boton}: nombre={name.group(1) if name else '?'!r}  "
                  f"Nos={seq}  Button={codigo}  "
                  f"-> {func_esp} {'OK' if ok else 'REVISAR'}   err={r.errors}")


if __name__ == "__main__":
    asyncio.run(main())
