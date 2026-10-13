"""Typed reads of console objects.

A telnet read has three outcomes and a bare ``str`` cannot tell them apart:

* the console answered with data
* the console had nothing for that object (``WARNING, NO OBJECTS FOUND FOR LIST``)
* the reply was cut off, mistimed, or never arrived

The second one is the dangerous one. ``NO OBJECTS FOUND`` is a perfectly
well-formed reply, so code that treats "I found nothing" as "it is empty" ends up
reporting a clean result over data it never received — a diff of two cues that do
not exist comes back as "these two cues are identical".

:class:`ObjectRead` makes the distinction a value the caller has to look at.

    read = await read_object(client, "cue", "3", sequence=156)
    if not read.found:
        return ...          # must decide what a missing object means here
    parse(read.raw)        # now `raw` really is the object's data
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# The console's refusal line for an empty listing (v3.9.60.50, live-verified
# 2026-10-08). Matched case-insensitively and as a substring: variants include
# "WARNING, NO OBJECTS FOUND FOR LIST" and a bare "NO OBJECTS FOUND".
_NO_OBJECTS_RE = re.compile(r"NO OBJECTS FOUND", re.IGNORECASE)

# `Error #N: TEXT` — the console's rejection format.
_ERROR_RE = re.compile(r"^\s*Error #(\d+)\s*:?\s*(.*)$", re.MULTILINE)

# ANSI colour codes. The console puts them between the words of its echo and
# after its prompt ("[Fixture]>\x1b[K"), so anything matched against a reply has
# to be read without them first.
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# Line of chrome around a reply that is not object data: the echo of our own
# command, the empty-listing refusal, an error, and the prompt. Read as a
# name/value row these invent attributes ("Executing", "NO") that look real.
_CHROME_LINE_RE = re.compile(
    r"^\s*(?:Executing\b|WARNING\s*,?\s*NO OBJECTS\b|No objects\b|Error #\d+)",
    re.IGNORECASE,
)

# The console prompt a reply ends with: "[Fixture]>", "[Channel]>", "Macro>".
_PROMPT_LINE_RE = re.compile(r"^\s*\[?[A-Za-z][\w ]*\]?>\s*$")


def _is_prompt_line(line: str) -> bool:
    """True when a line carries only the console prompt."""
    return bool(_PROMPT_LINE_RE.match(_ANSI_RE.sub("", line)))


def strip_chrome(raw: str) -> list[str]:
    """Reply lines that are object data, without echo, refusals or prompt.

    :func:`src.telnet_client.frame_reply` already drops everything before our
    own echo. This goes one step further for callers that parse the body: the
    prompt at the end and a refusal at the start are not data either.
    """
    out: list[str] = []
    for line in raw.splitlines():
        if not _ANSI_RE.sub("", line).strip():
            continue
        stripped = line.strip()
        if _CHROME_LINE_RE.match(_ANSI_RE.sub("", stripped)) or _is_prompt_line(stripped):
            continue
        out.append(_ANSI_RE.sub("", stripped).strip())
    return out


def cue_number(value: int | float | str) -> str:
    """A cue number as grandMA2 spells it.

    Tool signatures across the codebase type cue numbers as ``int``, ``float``
    or ``str``. A float whole cue arrives as ``3.0`` and interpolates into
    ``list cue 3.0 sequence N``, which names no cue. Sub-cues keep their
    decimal (``1.1``).
    """
    if isinstance(value, str):
        return value.strip()
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:g}"


def sequence_suffix(sequence: int | str | None) -> str:
    """The ``sequence N`` qualifier, or empty when there is no sequence."""
    return f" sequence {sequence}" if sequence is not None else ""


@dataclass(frozen=True)
class ObjectRead:
    """The result of one ``list`` read.

    Attributes:
        found: The console had the object. ``False`` means NO OBJECTS FOUND,
            which is an answer about the object, not an empty object.
        raw: The reply as received, unfiltered.
        lines: Data lines only (see :func:`strip_chrome`).
        error_code: MA2 ``Error #N`` code when the console rejected the command.
        error_text: The rest of that error line.
        command: The command that was sent.
    """

    found: bool
    raw: str
    lines: list[str] = field(default_factory=list)
    error_code: int | None = None
    error_text: str = ""
    command: str = ""

    @property
    def rejected(self) -> bool:
        """True when the console answered with an explicit error."""
        return self.error_code is not None

    @property
    def usable(self) -> bool:
        """True when there is real data behind this read."""
        return self.found and not self.rejected


def classify(raw: str, command: str = "") -> ObjectRead:
    """Turn a raw reply into an :class:`ObjectRead`.

    An empty reply is reported as *not found*: nothing arrived, which is a
    different thing from the console confirming that the object is empty. Callers
    that treat the two the same way report a clean result over a read that never
    happened.

    Callers that already have the reply can use this directly; the rest should
    use :func:`read_object`.
    """
    text = raw or ""
    match = _ERROR_RE.search(text)
    error_code = int(match.group(1)) if match else None
    error_text = match.group(2).strip() if match else ""
    found = bool(text.strip()) and not _NO_OBJECTS_RE.search(text)
    return ObjectRead(
        found=found,
        raw=text,
        lines=strip_chrome(text),
        error_code=error_code,
        error_text=error_text,
        command=command,
    )


async def read_object(
    client: Any,
    object_type: str,
    object_id: int | float | str | None,
    *,
    sequence: int | str | None = None,
    echo_command: str | None = None,
) -> ObjectRead:
    """Read one object from the console.

    Args:
        client: A connected :class:`src.telnet_client.GMA2TelnetClient`.
        object_type: MA2 keyword, e.g. ``"cue"``, ``"fixture"``, ``"group"``.
        object_id: Object number. Cue numbers go through :func:`cue_number`, so
            a float whole cue does not become ``3.0``.
        sequence: Optional sequence qualifier, emitted as ``sequence N``.
        echo_command: Command string to record on the result; defaults to the
            one that was sent.

    Returns:
        ObjectRead: :attr:`ObjectRead.found` is False when the console had
        nothing for this object. Callers must decide what that means rather than
        treating the reply as data.
    """
    if object_type == "cue":
        target = None if object_id is None else cue_number(object_id)
    else:
        target = None if object_id is None else str(object_id)

    command = echo_command or (
        f"list {object_type} {target}{sequence_suffix(sequence)}"
        if target is not None
        else None
    )
    if command is None:
        return ObjectRead(found=False, raw="", command="")

    raw = await client.send_command_with_response(command)
    return classify(raw, command)


async def read_cue(
    client: Any,
    sequence_id: int | str,
    cue_id: int | float | str,
) -> ObjectRead:
    """Read one cue out of a sequence."""
    return await read_object(
        client, "cue", cue_id, sequence=sequence_id,
        echo_command=f"list cue {cue_number(cue_id)} sequence {sequence_id}",
    )


async def list_cues(
    client: Any,
    sequence_id: int | str,
) -> ObjectRead:
    """List the cues of a sequence."""
    return await read_object(
        client, "cue", None, sequence=sequence_id,
        echo_command=f"list cue sequence {sequence_id}",
    )


_CUE_ID_IN_LISTING_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s", re.MULTILINE)


def cue_ids_in(raw: str, limit: int) -> list[str]:
    """Cue numbers from a ``list cue sequence N`` reply, as the console spells them.

    Deduplicated in first-seen order so a listing that repeats a cue does not
    make us read the same cue twice.
    """
    seen: dict[str, None] = {}
    for m in _CUE_ID_IN_LISTING_RE.finditer(raw or ""):
        seen.setdefault(m.group(1), None)
        if len(seen) >= limit:
            break
    return list(seen)
