"""Los parsers del REPO contra respuestas REALES de la consola.

Todo esto corre el código real del repo, no una reimplementación.
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from ma2_telnet import Ma2  # noqa: E402
from src.cue_reads import cue_ids_in  # noqa: E402


def mock(replies):
    client = MagicMock()

    async def reply(cmd):
        return replies.get(cmd.strip().lower(), "")

    client.send_command_with_response = AsyncMock(side_effect=reply)
    return client


async def capture():
    """Captura las respuestas reales que necesita cada herramienta."""
    c = Ma2()
    await c.connect()
    r = {}
    r["list sequence"] = (await c.cmd("list sequence")).raw
    r["list macro"] = (await c.cmd("list macro")).raw
    r["list cue sequence 156"] = (await c.cmd("list cue sequence 156")).raw
    r["list macro 1"] = (await c.cmd("list macro 1")).raw
    r["list cue 1 sequence 156"] = (await c.cmd("list cue 1 sequence 156")).raw
    r["list fixture"] = (await c.cmd("list fixture")).raw
    await c.close()
    return r


async def main():
    r = await capture()
    print("respuestas reales capturadas\n")

    print("=" * 74)
    print("1 — cue_ids_in() sobre un listado REAL de cues")
    print("=" * 74)
    real = r["list cue sequence 156"]
    print("  crudo:")
    for ln in real.splitlines():
        if ln.strip():
            print(f"    |{ln.strip()[:90]}")
    print(f"\n  cue_ids_in(real) = {cue_ids_in(real, 10)}")
    print(f"  (mis tests usaban '1  Cue1\\n2  Cue2' que SI matchea el patron)")

    print()
    print("=" * 74)
    print("2 — detect_tracking_leaks con la respuesta REAL")
    print("=" * 74)
    import src.server as srv

    with patch.object(srv, "get_client", return_value=mock(r)):
        out = json.loads(await srv.detect_tracking_leaks(sequence_id=156))
    print(f"  cues_checked    : {out['cues_checked']}")
    print(f"  total_leaks     : {out['total_leaks']}")
    print(f"  recommendation  : {out['recommendation']}")

    print()
    print("=" * 74)
    print("3 — find_unused_objects(sequence) con la respuesta REAL")
    print("=" * 74)

    class Snap:
        active_macros = []
        executor_state = {}
        sequences = None

    with patch.object(srv, "get_client", return_value=mock(r)), patch.object(
        srv, "_orchestrator", MagicMock(last_snapshot=Snap())
    ):
        out = json.loads(await srv.find_unused_objects(object_type="sequence"))
    print(f"  inspected        : {out['inspected']}")
    print(f"  candidate_unused : {len(out['candidate_unused'])}")
    print(f"  (el show tiene 165 secuencias)")
    if out["candidate_unused"]:
        print(f"  primeros: {out['candidate_unused'][:3]}")

    print()
    print("=" * 74)
    print("4 — find_unused_objects(macro) con la respuesta REAL")
    print("=" * 74)
    with patch.object(srv, "get_client", return_value=mock(r)), patch.object(
        srv, "_orchestrator", MagicMock(last_snapshot=Snap())
    ):
        out = json.loads(await srv.find_unused_objects(object_type="macro"))
    print(f"  inspected        : {out['inspected']}")
    print(f"  candidate_unused : {len(out['candidate_unused'])}")
    print(f"  unreadable       : {out.get('unreadable_objects')}")
    if out["candidate_unused"]:
        print(f"  primeros: {out['candidate_unused'][:3]}")

    print()
    print("=" * 74)
    print("5 — ¿qué prefijos usa la consola? (muestra de cada listing)")
    print("=" * 74)
    import re
    for clave in ("list sequence", "list macro", "list fixture", "list cue sequence 156"):
        filas = [ln.strip() for ln in r[clave].splitlines() if ln.strip()]
        prefijos = {}
        for ln in filas:
            m = re.match(r"^(\S+)\s+(\d+(?:\.\d+)?)\b", ln)
            if m:
                prefijos[m.group(1)] = prefijos.get(m.group(1), 0) + 1
        print(f"  {clave:<28} -> {prefijos}")


asyncio.run(main())