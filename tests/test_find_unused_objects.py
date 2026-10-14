"""Tests for find_unused_objects — the tool that recommends candidates for deletion.

A read that fails and a read that finds nothing must not look the same here.
The tool exists to propose deletions, so a macro whose body could not be read
being listed as "no inbound references" is a recommendation to destroy
something that may well be referenced.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

NOT_FOUND = "WARNING, NO OBJECTS FOUND FOR LIST\n\r\r [Fixture]>"
REJECTED = "Error #66: CANNOT ASSIGN\n\r\r [Fixture]>"


def _client(*replies: str) -> MagicMock:
    client = MagicMock()
    client.send_command_with_response = AsyncMock(side_effect=list(replies))
    return client


def _body(*lines: str) -> str:
    return "Executing : List macro 1\n\r\r" + "\n".join(lines) + "\n\r\r [Fixture]>"


class TestFindUnusedObjectsMacroReads:
    """A macro with an unreadable body must not become a deletion candidate."""

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_unreadable_body_is_excluded_from_candidates(
        self, mock_get_client, mock_orch
    ):
        from src.server import find_unused_objects

        snap = MagicMock()
        snap.active_macros = []
        snap.executor_state = {}
        mock_orch.last_snapshot = snap

        mock_get_client.return_value = _client(
            "1  Caller\n2  Referenced\n3  CannotRead\n",
            _body("Go Macro 2"),                          # macro 1 points at 2
            _body("nothing"),                             # 2 is referenced by 1
            NOT_FOUND,                                   # macro 3: unreadable
        )

        data = json.loads(await find_unused_objects(object_type="macro"))

        # 2 is referenced by 1, so only 1 is unreferenced; 3 was never read.
        candidates = {c["id"] for c in data["candidate_unused"]}
        assert candidates == {1}, data["candidate_unused"]
        assert data["unreadable_objects"] == [{"id": 3}]
        assert data["complete"] is False
        assert "excluded from the candidates" in " ".join(data["notes"])

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_rejected_body_is_excluded(self, mock_get_client, mock_orch):
        from src.server import find_unused_objects

        snap = MagicMock()
        snap.active_macros = []
        snap.executor_state = {}
        mock_orch.last_snapshot = snap

        mock_get_client.return_value = _client(
            "1  Refused\n",
            REJECTED,
        )

        data = json.loads(await find_unused_objects(object_type="macro"))

        assert data["candidate_unused"] == []
        assert data["unreadable_objects"] == [{"id": 1}]
        assert data["complete"] is False

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_all_readable_means_complete(self, mock_get_client, mock_orch):
        from src.server import find_unused_objects

        snap = MagicMock()
        snap.active_macros = []
        snap.executor_state = {}
        mock_orch.last_snapshot = snap

        mock_get_client.return_value = _client(
            "1  Caller\n2  Referenced\n",
            _body("Go Macro 2"),   # 2 is referenced by 1
            _body("nothing"),      # 2 references nothing itself
        )

        data = json.loads(await find_unused_objects(object_type="macro"))

        assert [c["id"] for c in data["candidate_unused"]] == [1]
        assert data["unreadable_objects"] == []
        assert data["complete"] is True

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_a_real_jump_still_keeps_its_target_out(self, mock_get_client, mock_orch):
        from src.server import find_unused_objects

        snap = MagicMock()
        snap.active_macros = []
        snap.executor_state = {}
        mock_orch.last_snapshot = snap

        mock_get_client.return_value = _client(
            "1  Caller\n2  Target\n",
            _body("Go Macro 2"),   # macro 1 references macro 2
            _body("nothing"),      # macro 2 itself references nothing
        )

        data = json.loads(await find_unused_objects(object_type="macro"))

        # macro 2 is referenced, so only macro 1 is a candidate
        assert [c["id"] for c in data["candidate_unused"]] == [1]

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_the_listing_echo_is_not_read_as_an_object_id(
        self, mock_get_client, mock_orch
    ):
        """The listing carries the command we just sent.

        "Executing : List macro" has no digits, but a listing that echoes a
        macro number would. Stripping chrome keeps ids out of the chrome.
        """
        from src.server import find_unused_objects

        snap = MagicMock()
        snap.active_macros = []
        snap.executor_state = {}
        mock_orch.last_snapshot = snap

        mock_get_client.return_value = _client(
            "Executing : List macro\n\r\r 1  Only\n\r\r [Fixture]>",
            _body("nothing"),
        )

        data = json.loads(await find_unused_objects(object_type="macro"))

        assert data["inspected"] == 1
        assert [c["id"] for c in data["candidate_unused"]] == [1]
