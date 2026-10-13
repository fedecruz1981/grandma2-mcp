r"""
Prueba si el comando `Effect N` (palabra clave pelada) mete un effect DENTRO
de un cue de secuencia.

Contexto: effect_test2.py probo 7 variantes de `Assign Effect ...` y ninguna
guardo nada. Pero ese script NO probo la forma que usa la consola de verdad:
seleccionar fixtures y escribir `Effect <n>` (equivale a apretar el boton del
pool de Effects). Cuando el operador lo hace a mano, el effect queda en el
programador como una capa y al grabar aparece en el XML como:

    <CueData ...>
      <Channel fixture_id="1" attribute_name="PAN" />
      <Value>86.4</Value>
      <Effect name="P/T Cross 17"><No>1</No><No>17</No></Effect>
      <EffectFlags form_index="22" sub_form_index="0" />
      <EffectRate>0.1</EffectRate>
      <EffectLow>-35</EffectLow>
      <EffectHigh>35</EffectHigh>
      <EffectPhase>-120</EffectPhase>
      <EffectWidth>100</EffectWidth>
    </CueData>

Formato confirmado en seq_0059.xml (show "cct obra matias"), verificado con
grep sobre los 155 exports. El tag a buscar en la verificacion es `<Effect`.

Aparte se exporta una secuencia VIVA con effects para probar que el formato
existe tambien en el show actual "fede inti y luna sep 2026".

Metodo: una secuencia distinta por caso, nunca Delete sobre inexistentes.
Uso: python scripts\effect_test3.py
"""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ma2_telnet import Ma2  # noqa: E402

EXPORT_DIR = Path(r"C:\ProgramData\MA Lighting Technologies"
                  r"\grandma\gma2_V_3.9.60\importexport")
SEQ0 = 190
FXS = "Fixture 23 Thru 30"


def tags(path: Path):
    if not path.exists():
        return None
    t = path.read_text(encoding="utf-8", errors="replace")
    return sorted({m for m in re.findall(r"<(\w*[Ee]ffect\w*)", t)})


# (etiqueta, lista de comandos que se mandan antes del Store)
CASOS = [
    ("Effect 2 pelado",          [FXS, "Effect 2"]),
    ("Effect 3 pelado",          [FXS, "Effect 3"]),
    ("Effect 6 pelado",          [FXS, "Effect 6"]),
    ("Effect 7 pelado",          [FXS, "Effect 7"]),
    ("Effect por nombre",        [FXS, 'Effect "Dimmer PWM"']),
    ("Effect 7 con Rate",        [FXS, "Effect 7 Rate 60"]),
    ("At Effect 7",              [FXS, "At Effect 7"]),
    ("Fixture Effect inline",    ["Clear", "Fixture 23 Thru 30 Effect 7"]),
]


async def main():
    async with Ma2() as ma2:
        await ma2.at_prompt()

        # --- referencia: una secuencia VIVA con effects ---
        print("=" * 78)
        print("REFERENCIA: export de la secuencia 58 (ARCO IRIS LED) del show vivo")
        await ma2.cmd("cd /")
        await ma2.cmd('Export Sequence 58 "ref58"')
        r = EXPORT_DIR / "ref58.xml"
        print(f"  tags de effect en ref58.xml: {tags(r)}")

        print("\n" + "=" * 78)
        print("POOL DE EFFECTS en el show vivo:")
        await ma2.cmd("cd /")
        r = await ma2.cmd("list effect")
        for ln in [x for x in r.body if x.strip()]:
            print(f"  {ln.strip()[:110]}")

        creadas = []
        print("\n" + "=" * 78)
        print("PRUEBAS: se graba el cue 1 y se busca <Effect en el XML")
        for i, (etiqueta, cmds) in enumerate(CASOS):
            seq = SEQ0 + i
            tag = f"eft3_{i}"
            print("-" * 78)
            print(f"CASO {i}: {etiqueta}   ->  Sequence {seq}")
            await ma2.cmd("cd /")
            await ma2.cmd("Clear")
            for c in cmds:
                r = await ma2.cmd(c)
                estado = "ok" if not r.errors else "ERR " + str(r.errors)
                print(f"  >>> {c:<34} [{estado}]")
                for ln in [x for x in r.body if x.strip()][:3]:
                    print(f"        {ln.strip()[:120]}")
            r = await ma2.cmd(f"Store Cue 1 Sequence {seq} /noconfirm")
            print(f"  >>> Store Cue 1 Sequence {seq} /noconfirm "
                  f"[{'ok' if not r.errors else 'ERR ' + str(r.errors)}]")
            await ma2.cmd("cd /")
            await ma2.cmd(f'Export Sequence {seq} "{tag}"')
            creadas.append(seq)
            t = tags(EXPORT_DIR / f"{tag}.xml")
            hay = bool(t and any(x == "Effect" for x in t))
            print(f"  --> tags: {t if t else 'NINGUNO'}"
                  f"   {'*** FUNCIONA ***' if hay else '(no-op)'}")

        print("\n" + "=" * 78)
        print("LIMPIEZA (estas secuencias existen, borrarlas es seguro)")
        for seq in creadas:
            await ma2.cmd("cd /")
            await ma2.cmd(f"Delete Sequence {seq}")


if __name__ == "__main__":
    asyncio.run(main())
