"""
Telnet robustness: dropped sockets, cut-off replies, rejected logins.

Readers are MagicMocks; ``at_eof`` is set explicitly where a test needs it
(a bare MagicMock's at_eof() is truthy, so the client only trusts ``True``).
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telnet_client import GMA2TelnetClient, collect_transport_warnings


def _client(read_side_effect, eof: bool = False) -> GMA2TelnetClient:
    client = GMA2TelnetClient(host="127.0.0.1")
    reader = MagicMock()
    reader.read = AsyncMock(side_effect=read_side_effect)
    reader.at_eof = MagicMock(return_value=eof)
    writer = MagicMock()
    writer.is_closing = MagicMock(return_value=False)
    client._reader, client._writer, client._connection = reader, writer, True
    return client


async def _send(client, cmd="list cue"):
    return await client.send_command_with_response(cmd, timeout=0.05, delay=0, subsequent_timeout=0.01)


class TestDroppedConnection:
    def test_is_connected_false_when_reader_at_eof(self):
        assert _client([], eof=True).is_connected is False

    def test_is_connected_false_when_writer_closing(self):
        client = _client([])
        client._writer.is_closing.return_value = True
        assert client.is_connected is False

    def test_is_connected_true_for_plain_mocks(self):
        client = GMA2TelnetClient(host="127.0.0.1")
        client._reader, client._writer, client._connection = MagicMock(), MagicMock(), True
        assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_eof_before_send_raises_connection_error(self):
        client = _client([], eof=True)
        with pytest.raises(ConnectionError, match="closed"):
            await _send(client)
        assert client._writer is None  # marked dropped so the session manager reconnects

    @pytest.mark.asyncio
    async def test_eof_during_read_with_no_data_raises(self):
        client = _client([TimeoutError(), ""])
        client._reader.at_eof.side_effect = [False, True, True]
        with pytest.raises(ConnectionError):
            await _send(client)


class TestEchoMismatch:
    """The console echoed something other than what we sent.

    A malformed command does not fail: the console answers whatever it made of
    the line, and the reply reads like a real answer to the wrong question.
    """

    def _echo(self, keyword: str) -> str:
        return f"Executing : \x1b[32m{keyword}\x1b[37m 1\n\r\r [Fixture]>\x1b[K"

    @pytest.mark.asyncio
    async def test_matching_echo_does_not_warn(self):
        client = _client([TimeoutError(), self._echo("List") + "\r\nCue 1\r\n[Channel]>", TimeoutError()])
        with collect_transport_warnings() as warnings:
            await _send(client, "list cue")
        assert warnings == []

    @pytest.mark.asyncio
    async def test_reply_without_any_echo_does_not_warn(self):
        # Plenty of MA2 keywords answer with no Executing marker at all.
        client = _client([TimeoutError(), "Cue 1\r\n[Channel]>", TimeoutError()])
        with collect_transport_warnings() as warnings:
            await _send(client, "list cue")
        assert warnings == []

    @pytest.mark.asyncio
    async def test_echo_of_another_keyword_warns(self):
        # We asked to "list", the console echoed "Store": it read the line as
        # something else, so the body we got back answers another question.
        client = _client([TimeoutError(), self._echo("Store") + "\r\nCue 1\r\n[Channel]>", TimeoutError()])
        with collect_transport_warnings() as warnings:
            await _send(client, "list cue")
        assert any("did not echo" in w and "list" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_stale_echo_of_another_session_does_not_warn(self):
        # Another session's echo names another keyword; ours is missing. The
        # mismatch is real, but it is the stale line we want to report on, not
        # this tool call — still worth saying so, since our own reply is absent.
        stale = "Executing : \x1b[32mStore\x1b[37m Sequence 136\n\r\r [Fixture]>\x1b[K"
        client = _client([TimeoutError(), stale + "\r\nCue 1\r\n[Channel]>", TimeoutError()])
        with collect_transport_warnings() as warnings:
            raw = await _send(client, "list cue")
        assert raw.startswith(stale)
        assert any("did not echo" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_abbreviated_keyword_counts_as_ours(self):
        # We send "cd", the console echoes the canonical "ChangeDest".
        client = _client([
            TimeoutError(),
            "Executing : \x1b[32mChangeDest\x1b[37m / 3\r\n\r [Fixture]>\x1b[K",
            TimeoutError(),
        ])
        with collect_transport_warnings() as warnings:
            await _send(client, "cd / 3")
        assert warnings == []


class TestEchoMatchesCommandUnit:
    """The predicate itself, without the socket."""

    def test_no_command_is_not_a_mismatch(self):
        from src.telnet_client import echo_matches_command

        assert echo_matches_command("Executing : List 1", "") is True

    def test_other_session_echo_alongside_ours_is_a_match(self):
        from src.telnet_client import echo_matches_command

        raw = "Executing : Store 1\n\r\r [Fixture]>\r\rExecuting : List 1\n\r\rCue 1\r\r [Channel]>"
        assert echo_matches_command(raw, "list cue") is True

    def test_only_our_own_echo_is_required(self):
        from src.telnet_client import echo_matches_command

        raw = "Executing : Goto cue 3 sequence 156\n\r\r [Fixture]>\x1b[K"
        assert echo_matches_command(raw, "list cue") is False


class TestCutOffReplies:
    @pytest.mark.asyncio
    async def test_complete_reply_has_no_warning(self):
        client = _client([TimeoutError(), "Cue 1\r\n[Channel]>", TimeoutError()])
        with collect_transport_warnings() as warnings:
            assert (await _send(client)).endswith("[Channel]>")
        assert warnings == []

    @pytest.mark.asyncio
    async def test_reply_without_prompt_waits_then_warns(self):
        client = _client([TimeoutError(), "Cue 1\r\nCue 2", TimeoutError(), TimeoutError()])
        with collect_transport_warnings() as warnings:
            raw = await _send(client)
        assert raw == "Cue 1\r\nCue 2"
        assert any("prompt" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_late_tail_is_collected_during_settle_wait(self):
        client = _client([TimeoutError(), "Cue 1\r\n", TimeoutError(), "Cue 2\r\n[Channel]>", TimeoutError()])
        with collect_transport_warnings() as warnings:
            raw = await _send(client)
        assert raw.endswith("[Channel]>")
        assert warnings == []

    @pytest.mark.asyncio
    async def test_empty_reply_warns(self):
        client = _client([TimeoutError(), TimeoutError()])
        with collect_transport_warnings() as warnings:
            assert await _send(client) == ""
        assert any("no reply" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_angle_and_ansi_prompts_count_as_complete(self):
        client = _client([TimeoutError(), "ok\r\n\x1b[32mFixture>\x1b[0m ", TimeoutError()])
        with collect_transport_warnings() as warnings:
            await _send(client)
        assert warnings == []

    @pytest.mark.asyncio
    async def test_warnings_outside_a_collector_are_ignored(self):
        client = _client([TimeoutError(), TimeoutError()])
        assert await _send(client) == ""  # must not raise without a collector


class TestTransportWarningsInToolReplies:
    @pytest.mark.asyncio
    async def test_handle_errors_attaches_transport_warnings(self):
        from src.server import _handle_errors
        from src.telnet_client import record_transport_warning

        @_handle_errors
        async def tool() -> str:
            record_transport_warning("reply ended without a console prompt")
            return json.dumps({"command_sent": "list", "raw_response": "partial"})

        data = json.loads(await tool())
        assert data["transport_warnings"] == ["reply ended without a console prompt"]
        assert data["ok"] is True


class TestRejectedLogin:
    @pytest.mark.asyncio
    @patch("src.telnet_client.telnetlib3.open_connection")
    async def test_login_sets_rejected_flag(self, mock_open):
        reader, writer = MagicMock(), MagicMock()
        reader.read = AsyncMock(return_value="Error #9: LOGIN FAILED")
        mock_open.return_value = (reader, writer)
        client = GMA2TelnetClient(host="127.0.0.1")
        await client.connect()
        assert await client.login() is False
        assert client.login_rejected is True

    @pytest.mark.asyncio
    async def test_session_manager_raises_on_rejected_login(self):
        from src.session_manager import SessionManager

        fake = MagicMock()
        fake.connect = AsyncMock()
        fake.disconnect = AsyncMock()

        async def _login():
            fake.login_rejected = True
            return False

        fake.login = AsyncMock(side_effect=_login)
        with patch("src.session_manager.GMA2TelnetClient", return_value=fake):
            manager = SessionManager(host="127.0.0.1", port=30000)
            with pytest.raises(ConnectionError, match="rejected login"):
                await manager.get("op", "baduser", "badpass")
        fake.disconnect.assert_awaited()

    @pytest.mark.asyncio
    async def test_session_manager_accepts_unverified_login(self):
        """MA2 may stay silent on success — a timeout must not be treated as rejection."""
        from src.session_manager import SessionManager

        fake = MagicMock()
        fake.connect = AsyncMock()
        fake.login = AsyncMock(return_value=False)
        fake.login_rejected = False
        with patch("src.session_manager.GMA2TelnetClient", return_value=fake):
            manager = SessionManager(host="127.0.0.1", port=30000)
            assert await manager.get("op", "user", "pw") is fake
