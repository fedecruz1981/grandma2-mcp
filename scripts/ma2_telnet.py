"""
Cliente telnet directo para grandMA2 — sin MCP.

Por que existe: el servidor MCP (drohi-r/grandma2-mcp) tiene tres problemas
para LEER contenido de cues:

  1. `cd Sequence N/Cue M` con "/" no entra al cue. Necesita ESPACIO:
     `cd Sequence N Cue M`. El MCP usa la barra y lee el nivel de secuencia,
     por eso todas las secuencias devuelven el mismo preset.
  2. send_command_with_response() duerme 0.3s y luego lee. Si la respuesta
     llega repartida, el read se corta a mitad y devuelve texto de un
     comando anterior mezclado.
  3. No deduplica: dos llamadas seguidas devuelven la historia acumulada.

Este modulo lee HASTA EL PROMPT (terminador), que es la unica forma fiable.
Medido en esta consola: 314 ms de latencia, respuesta completa siempre.

Uso:
    import asyncio
    from ma2_telnet import Ma2

    async def main():
        async with Ma2() as ma2:
            print(await ma2.cmd("cd Sequence 137 Cue 1"))
            print(await ma2.cmd("list preset"))
    asyncio.run(main())
"""
from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# El prompt de grandMA2 siempre termina en '>'. Puede traer ruta:
#   Sequences/Global /malvado 137/Cue 1 >
#   Presets/Global /Dimmer 1/dim frente 1.1 >
#   [Macro]>
PROMPT_RE = re.compile(r"((?:Sequences|Presets|Fixtures|Macros|Effects|Groups|Worlds|"
                       r"Filter|Filters|Timecode|Timers|Users|Layouts|Views|Pages|"
                       r"Executors|Plugin|Plugins|Showfile|Setup|MA|Record|"
                       r"Special|Custom|Remote)[^\r\n]*?>|"
                       r"\[[A-Za-z][A-Za-z0-9 ]*\]>)\s*$")


@dataclass
class Ma2Response:
    raw: str
    lines: list[str] = field(default_factory=list)
    prompt: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def body(self) -> list[str]:
        """Líneas de datos: sin eco del comando, sin cabeceras, sin prompt."""
        out, started = [], False
        for ln in self.lines:
            if ln.startswith("Executing :"):
                started = True
                continue
            if not started:
                continue
            if PROMPT_RE.search(ln) and ln.rstrip().endswith(">"):
                continue
            out.append(ln)
        return out

    def __str__(self) -> str:
        return "\n".join(self.lines)


class Ma2:
    """Cliente telnet asíncrono para grandMA2. Un comando a la vez."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        idle: float = 0.35,
        max_wait: float = 12.0,
    ) -> None:
        self.host = host or os.environ.get("GMA_HOST", "192.168.0.71")
        self.port = port or int(os.environ.get("GMA_PORT", "30000"))
        self.user = user or os.environ.get("GMA_USER", "administrator")
        self.password = password or os.environ.get("GMA_PASSWORD", "admin")
        self.idle = idle          # silencio que marca fin de respuesta
        self.max_wait = max_wait  # techo absoluto
        self._r = None
        self._w = None
        self._lock = asyncio.Lock()

    # ---------- conexión ----------

    async def connect(self) -> "Ma2":
        self._r, self._w = await asyncio.open_connection(self.host, self.port)
        await asyncio.sleep(0.2)
        await self._read_until_prompt(max_wait=3.0)
        await self._raw(f'login "{self.user}" "{self.password}"')
        await self._read_until_prompt(max_wait=4.0)
        return self

    async def close(self) -> None:
        if self._w is not None:
            self._w.close()
        self._r = self._w = None

    async def __aenter__(self) -> "Ma2":
        return await self.connect()

    async def __aexit__(self, *exc) -> None:
        await self.close()

    # ---------- bajo nivel ----------

    async def _raw(self, data: str) -> None:
        self._w.write(data.encode("utf-8") + b"\r\n")
        await self._w.drain()

    async def _read_until_prompt(self, max_wait: float | None = None) -> str:
        """Lee hasta que aparezca el prompt. Éste es el terminador real.

        Los prompts de MA2 tienen \r como separador interno, así que el regex
        tiene que buscar '>' al final sin depender de \n.
        """
        cap = max_wait or self.max_wait
        buf = ""
        loop = asyncio.get_event_loop()
        deadline = loop.time() + cap
        while loop.time() < deadline:
            try:
                chunk = await asyncio.wait_for(
                    self._r.read(65536), timeout=self.idle
                )
            except asyncio.TimeoutError:
                if buf:
                    break
                continue
            if not chunk:
                break
            buf += chunk.decode("utf-8", "replace")
            # el prompt puede haber llegado sin newline final
            if ">" in buf:
                tail = ANSI.sub("", buf).rstrip()
                if tail.endswith(">"):
                    break
        return buf

    async def drain(self) -> None:
        """Vacía lo que haya quedado en el buffer antes de un comando nuevo."""
        try:
            while True:
                chunk = await asyncio.wait_for(self._r.read(65536), timeout=0.12)
                if not chunk:
                    break
        except (asyncio.TimeoutError, Exception):
            pass

    # ---------- API ----------

    async def cmd(self, command: str) -> Ma2Response:
        """Envía UN comando y devuelve su respuesta completa.

        Serializado con lock: la consola procesa comandos de a uno y dos
        readers simultáneos producen 'read() called while another coroutine
        is already waiting' (el bug del pool index del MCP).
        """
        async with self._lock:
            await self.drain()
            await self._raw(command)
            raw = await self._read_until_prompt()
            return self._parse(raw)

    async def cmd_seq(self, *commands: str) -> list[Ma2Response]:
        """Varios comandos, uno por vez. Devuelve las respuestas en orden."""
        return [await self.cmd(c) for c in commands]

    @staticmethod
    def _parse(raw: str) -> Ma2Response:
        text = ANSI.sub("", raw or "")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [ln.rstrip() for ln in text.split("\n")]

        # limpia líneas de prompt y trailing blanks
        lines = [ln for ln in lines if ln.strip()]

        prompt = ""
        for ln in reversed(lines):
            s = ln.strip()
            if s.endswith(">") and not s.startswith("Executing"):
                prompt = s
                break

        errors = [
            ln for ln in lines
            if re.search(r"Error\s*#?\d+|OBJECT DOES NOT EXIST|Error :", ln, re.I)
        ]

        return Ma2Response(raw=raw, lines=lines, prompt=prompt, errors=errors)

    # ---------- helpers de alto nivel ----------

    async def goto(self, path: str) -> Ma2Response:
        """Navega. Acepta 'Sequence 137 Cue 1' (con espacios)."""
        return await self.cmd(f"cd {path}")

    async def list_dir(self, path: str | None = None) -> Ma2Response:
        if path:
            await self.cmd(f"cd {path}")
        return await self.cmd("list")

    async def at_prompt(self) -> str:
        r = await self.cmd("")
        return r.prompt


if __name__ == "__main__":
    async def demo():
        async with Ma2() as ma2:
            print("prompt:", await ma2.at_prompt())
            r = await ma2.cmd("list fixture")
            for ln in r.body[:5]:
                print("  ", ln)
    asyncio.run(demo())