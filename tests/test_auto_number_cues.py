"""Tests for auto_number_cues — the DESTRUCTIVE cue renumbering tool."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

LISTING = "1 Cue1\n2 Cue2\n3 Cue3\n"
MOVE_REPLY = "Executing : Move cue 1 sequence 1 at cue 2 sequence 1\n\r\r [Fixture]>"


def _client(listing: str) -> MagicMock:
    """A client that answers the listing once, then every move alike.

    auto_number_cues sends one `list` followed by one `move` per cue that
    actually has to move, so the mock cannot return the listing for all of them.
    """
    client = MagicMock()

    async def reply(cmd: str) -> str:
        return listing if cmd.lower().startswith("list") else MOVE_REPLY

    client.send_command_with_response = AsyncMock(side_effect=reply)
    return client


class TestAutoNumberCuesNumbering:
    """A whole cue must never be renumbered as "cue 3.0".

    The tool parses cue IDs out of a listing and builds `move cue` commands
    with them. Parsed as floats and interpolated back, cue 3 becomes 3.0 and
    every move command names a cue that does not exist.
    """

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_move_commands_carry_no_decimal(self, mock_get_client):
        from src.server import auto_number_cues

        mock_get_client.return_value = _client("1 Cue1\n2 Cue2\n3 Cue3\n")

        data = json.loads(
            await auto_number_cues(sequence_id=1, start=1, spacing=1, confirm_destructive=True)
        )

        for cmd in data["commands"]:
            assert ".0 " not in cmd, cmd
            assert "move cue 1 " in cmd or "move cue 2 " in cmd or "move cue 3 " in cmd, cmd

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_old_to_new_keys_have_no_decimal(self, mock_get_client):
        from src.server import auto_number_cues

        mock_get_client.return_value = _client("1 Cue1\n2 Cue2\n3 Cue3\n")

        data = json.loads(
            await auto_number_cues(sequence_id=1, start=10, spacing=5, confirm_destructive=True)
        )

        assert all("." not in key for key in data["old_to_new"]), data["old_to_new"]
        assert set(data["old_to_new"]) == {"1", "2", "3"}

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_cue_10_is_renumbered_after_cue_9_not_between_1_and_2(self, mock_get_client):
        """Numeric order, not string order.

        Parsed as strings and sorted, "10" lands between "1" and "2", and the
        renumbering walks the sequence in the wrong order — which for a
        destructive move is the difference between renumbering and scrambling.
        """
        from src.server import auto_number_cues

        mock_get_client.return_value = _client(
            "1 Cue1\n2 Cue2\n9 Cue9\n10 Cue10\n"
        )

        data = json.loads(
            await auto_number_cues(sequence_id=1, start=1, spacing=1, confirm_destructive=True)
        )

        assigned = {int(v) for v in data["old_to_new"].values()}
        assert assigned == {1, 2, 3, 4}
        assert set(data["old_to_new"]) == {"1", "2", "9", "10"}

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_the_console_echo_is_not_read_as_a_cue(self, mock_get_client):
        """The listing's own "Executing : List cue sequence 1" is not cue 1.

        The echo carries digits after the keyword, so a loose parse reads a cue
        number out of the command the agent itself just sent.
        """
        from src.server import auto_number_cues

        mock_get_client.return_value = _client(
            "Executing : List cue sequence 1\n\r\r 1 Cue1\n\r\r 2 Cue2\n\r\r [Fixture]>"
        )

        data = json.loads(
            await auto_number_cues(sequence_id=1, start=1, spacing=1, confirm_destructive=True)
        )

        assert set(data["old_to_new"]) == {"1", "2"}

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_empty_sequence_is_blocked_before_any_move(self, mock_get_client):
        from src.server import auto_number_cues

        client = _client("NO OBJECTS FOUND")
        mock_get_client.return_value = client

        data = json.loads(
            await auto_number_cues(sequence_id=9, start=1, spacing=1, confirm_destructive=True)
        )

        assert data["blocked"] is True
        assert client.send_command_with_response.call_count == 1  # only the list


class TestAutoNumberCuesGating:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_requires_confirmation(self, mock_get_client):
        from src.server import auto_number_cues

        mock_get_client.return_value = _client("1 Cue1\n")

        data = json.loads(await auto_number_cues(sequence_id=1, start=1, spacing=1))

        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"
