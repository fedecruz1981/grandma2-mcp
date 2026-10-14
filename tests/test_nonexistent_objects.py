"""Lo que la consola responde cuando se le pide algo que no existe.

Medido en vivo contra grandMA2 3.9.60.82, show "inti y luna oct2026",
secuencia 156 (6 cues).

    list cue 1    sequence 156  -> la fila del cue 1
    list cue 99   sequence 156  -> WARNING, NO OBJECTS FOUND FOR LIST
    list cue 0    sequence 156  -> VACIO
    list cue 1.99 sequence 156  -> VACIO
    list cue 999  ...           -> VACIO

    list cue abc  sequence 156  -> LAS SEIS filas de la secuencia
    list cue -1   sequence 156  -> LAS SEIS filas de la secuencia

Un cue no numÃ©rico o negativo no nombra un cue: la consola cae a listar la
secuencia entera. La respuesta estÃ¡ bien formada, no trae error, y no es sobre
el cue pedido. Cualquier herramienta que decida "el cue existe" mirando que no
haya NO OBJECTS FOUND estÃ¡ confirmando un cue que nadie nombrÃ³.

Y el eco no sirve para detectar un comando invÃ¡lido:

    > NotAKeyword 1
    Executing : NotAKeyword 1     <-- lo repite tal cual
    Error #1: UNKNOWN COMMAND

El eco de una keyword desconocida es idÃ©ntico al de una vÃ¡lida, asÃ­ que
echo_matches_command no las distingue. Lo Ãºnico que difiere es la lÃ­nea de error.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cue_reads import asks_for_cue, object_ids_in
from src.telnet_client import console_rejected, echo_matches_command


def _listing(*cue_numbers: str) -> str:
    rows = "\n".join(
        f"Cue {n} {n}       *    Go              Normal  None  Infinite  Infinite   ({i})"
        for i, n in enumerate(cue_numbers, start=1)
    )
    return (
        "Executing : \x1b[32mList\x1b[37m \x1b[32mCue\x1b[37m 1 \x1b[32mSequence\x1b[37m 156\r\n\r\n"
        "      Number  MIB  Trig  TrigTime  Mode    Loop  Lcount    Ltime     \r\n\r\n"
        f"{rows}\r\n\r\n \x1b[32mMacro\x1b[37m>\x1b[K"
    )


SIX_CUES = _listing("1", "2", "3", "4", "5", "6")
NO_OBJECTS = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mCue\x1b[37m 99 \x1b[32mSequence\x1b[37m 156\r\n\r\n"
    "WARNING, NO OBJECTS FOUND FOR LIST\r\n\r\n \x1b[32mMacro\x1b[37m>\x1b[K"
)


class TestAsksForCue:
    """A listing that names the cue we asked for is an answer about it."""

    def test_the_asked_cue_is_in_the_listing(self):
        assert asks_for_cue(SIX_CUES, "1") is True
        assert asks_for_cue(SIX_CUES, "6") is True

    def test_a_cue_not_in_the_listing_is_not_an_answer(self):
        assert asks_for_cue(SIX_CUES, "99") is False
        assert asks_for_cue(SIX_CUES, "0") is False

    def test_non_numeric_id_falls_back_to_the_whole_listing(self):
        """The live case: 'list cue abc' returns every row in the sequence."""
        assert asks_for_cue(SIX_CUES, "abc") is False

    def test_negative_id_falls_back_too(self):
        assert asks_for_cue(SIX_CUES, "-1") is False

    def test_sub_cue_is_compared_as_written(self):
        listing = _listing("1", "1.1", "2")
        assert asks_for_cue(listing, "1.1") is True
        assert asks_for_cue(listing, "1") is True
        assert asks_for_cue(listing, "1.2") is False

    def test_float_whole_cue_matches(self):
        assert asks_for_cue(SIX_CUES, 1.0) is True

    def test_empty_listing(self):
        assert asks_for_cue(NO_OBJECTS, "1") is False


class TestTheSilentFallbackIsReal:
    """What the console actually sent back, as captured live."""

    def test_a_garbage_id_looks_identical_to_a_good_one(self):
        # Both are well-formed, neither has NO OBJECTS, both carry cue rows.
        assert "NO OBJECTS" not in SIX_CUES.upper()
        assert "NO OBJECTS" not in SIX_CUES.upper()

    def test_but_only_one_of_them_is_about_the_cue_asked(self):
        # The reply says nothing about which cue was asked for, which is the
        # whole reason asks_for_cue exists.
        assert len(object_ids_in(SIX_CUES, 20)) == 6


class TestListSequenceCuesExistence:
    """list_sequence_cues must not confirm a cue the console never named."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_a_garbage_cue_is_not_reported_as_existing(self, mock_get_client):
        from src.server import list_sequence_cues

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=SIX_CUES)
        mock_get_client.return_value = mock_client

        data = json.loads(
            await list_sequence_cues(sequence_id=156, cue_id="abc")
        )

        assert data["exists"] is False

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_a_negative_cue_is_not_reported_as_existing(self, mock_get_client):
        from src.server import list_sequence_cues

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=SIX_CUES)
        mock_get_client.return_value = mock_client

        data = json.loads(await list_sequence_cues(sequence_id=156, cue_id=-1))

        assert data["exists"] is False

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_a_real_cue_is_still_found(self, mock_get_client):
        from src.server import list_sequence_cues

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=SIX_CUES)
        mock_get_client.return_value = mock_client

        data = json.loads(await list_sequence_cues(sequence_id=156, cue_id=3))

        assert data["exists"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_a_cue_beyond_the_end_is_not_found(self, mock_get_client):
        from src.server import list_sequence_cues

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=SIX_CUES)
        mock_get_client.return_value = mock_client

        data = json.loads(await list_sequence_cues(sequence_id=156, cue_id=99))

        assert data["exists"] is False

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_listing_the_whole_sequence_still_works(self, mock_get_client):
        """No cue_id means 'list the sequence', not a claim about one cue."""
        from src.server import list_sequence_cues

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=SIX_CUES)
        mock_get_client.return_value = mock_client

        data = json.loads(await list_sequence_cues(sequence_id=156))

        assert data["exists"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_a_genuinely_absent_cue_still_reports_absent(self, mock_get_client):
        """The NO OBJECTS case keeps working, not just the fallback case."""
        from src.server import list_sequence_cues

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=NO_OBJECTS)
        mock_get_client.return_value = mock_client

        data = json.loads(await list_sequence_cues(sequence_id=156, cue_id=99))

        assert data["exists"] is False

class TestConsoleRejected:
    """The echo cannot spot a bad keyword; the error line can."""

    UNKNOWN_KEYWORD = (
        "Executing : NotAKeyword 1\r\n\r\r\x1b[31mError : NotAKeyword 1\x1b[37m\r\n"
        "Error #1: UNKNOWN COMMAND\r\n\r \x1b[32mMacro\x1b[37m>\x1b[K"
    )
    OBJECT_MISSING = (
        "Executing : \x1b[32mList\x1b[37m \x1b[32mCue\x1b[37m 1"
        " \x1b[32mSequence\x1b[37m abc\r\n\r\r\x1b[31mError : List Cue 1 Sequence abc\x1b[37m\r\n"
        "Error #14: OBJECT DOES NOT EXIST\r\n\r \x1b[32mMacro\x1b[37m>\x1b[K"
    )
    VALID = _listing("1")

    def test_unknown_keyword_is_a_rejection(self):
        rejected, code, text = console_rejected(self.UNKNOWN_KEYWORD)
        assert rejected is True
        assert code == 1
        assert "UNKNOWN COMMAND" in text

    def test_object_missing_is_a_rejection(self):
        rejected, code, text = console_rejected(self.OBJECT_MISSING)
        assert rejected is True
        assert code == 14

    def test_a_valid_reply_is_not_a_rejection(self):
        assert console_rejected(self.VALID)[0] is False

    def test_an_empty_reply_is_not_a_rejection(self):
        assert console_rejected("")[0] is False

    def test_ansi_around_the_error_is_stripped(self):
        rejected, code, text = console_rejected(self.UNKNOWN_KEYWORD)
        assert "\x1b" not in text

    def test_the_echo_cannot_tell_them_apart(self):
        """Both echo the sent keyword verbatim. This is why the check exists."""
        assert echo_matches_command(self.UNKNOWN_KEYWORD, "NotAKeyword 1") is True
        assert echo_matches_command(self.VALID, "list cue 1 sequence 156") is True


class TestTransportWarnsOnRejection:
    @pytest.mark.asyncio
    async def test_a_rejection_is_surfaced_as_a_warning(self):
        from src.telnet_client import GMA2TelnetClient, collect_transport_warnings

        client = GMA2TelnetClient(host="127.0.0.1")
        reader = MagicMock()
        reader.read = AsyncMock(
            side_effect=[
                TimeoutError(),
                "Executing : NotAKeyword 1\r\n\rError #1: UNKNOWN COMMAND\r\n\r [Macro]>",
                TimeoutError(),
            ]
        )
        reader.at_eof = MagicMock(return_value=False)
        writer = MagicMock()
        writer.is_closing = MagicMock(return_value=False)
        client._reader, client._writer, client._connection = reader, writer, True

        with collect_transport_warnings() as warnings:
            await client.send_command_with_response(
                "NotAKeyword 1", timeout=0.05, delay=0, subsequent_timeout=0.01
            )

        assert any("rejected" in w and "UNKNOWN COMMAND" in w for w in warnings), warnings

    @pytest.mark.asyncio
    async def test_a_valid_command_produces_no_rejection_warning(self):
        from src.telnet_client import GMA2TelnetClient, collect_transport_warnings

        client = GMA2TelnetClient(host="127.0.0.1")
        reader = MagicMock()
        reader.read = AsyncMock(
            side_effect=[
                TimeoutError(),
                "Executing : List Cue 1 Sequence 156\r\n\rCue 1 1 * Go\r\n\r [Macro]>",
                TimeoutError(),
            ]
        )
        reader.at_eof = MagicMock(return_value=False)
        writer = MagicMock()
        writer.is_closing = MagicMock(return_value=False)
        client._reader, client._writer, client._connection = reader, writer, True

        with collect_transport_warnings() as warnings:
            await client.send_command_with_response(
                "list cue 1 sequence 156", timeout=0.05, delay=0, subsequent_timeout=0.01
            )

        assert not any("rejected" in w for w in warnings), warnings
