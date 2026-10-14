"""Tests for plan_fixture_swap.

The tool answers "is this swap safe?". It must never answer that question about
a fixture type it failed to read: an empty attribute set is indistinguishable
from a fixture type that genuinely has no attributes, and the difference is
between "risk high, adjust six attributes by hand" and "I don't know".
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

OLD_TYPE = "Mac 700 Profile"
NEW_TYPE = "Mac Viper"


def _fixture_listing(*type_names: str) -> str:
    rows = "\n".join(f"{i}  {n}" for i, n in enumerate(type_names, start=1))
    return f"Executing : List fixture\n\r\r{rows}\n\r\r [Fixture]>"


def _info(fixture_id: int, *attrs: str) -> str:
    rows = "\n".join(f"Attribute={a}" for a in attrs)
    return f"Executing : Info fixture {fixture_id}\n\r\r{rows}\n\r\r [Fixture]>"


def _client(*replies: str) -> MagicMock:
    client = MagicMock()
    client.send_command_with_response = AsyncMock(side_effect=list(replies))
    return client


# cd / , list fixture , info fixture , cd /
def _both_readable() -> list[str]:
    return [
        "cd /", _fixture_listing(OLD_TYPE, NEW_TYPE), _info(1, "Dimmer", "Pan", "Tilt"), "cd /",
        "cd /", _fixture_listing(OLD_TYPE, NEW_TYPE), _info(2, "Dimmer", "Pan", "Gobo"), "cd /",
    ]


class TestPlanFixtureSwapReadable:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_comparable_types_get_a_verdict(self, mock_get_client):
        from src.server import plan_fixture_swap

        mock_get_client.return_value = _client(*_both_readable())

        data = json.loads(
            await plan_fixture_swap(old_fixture_type=OLD_TYPE, new_fixture_type=NEW_TYPE)
        )

        assert set(data["compatible_attributes"]) == {"Dimmer", "Pan"}
        assert set(data["missing_in_new"]) == {"Tilt"}
        assert set(data["new_only_attributes"]) == {"Gobo"}
        assert data["compatibility_percent"] == round(2 / 3 * 100, 1)
        assert data["risk_level"] in {"low", "medium", "high"}


class TestPlanFixtureSwapUnreadable:
    """One side unreadable must not become "the other type has no attributes"."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_new_type_not_patched(self, mock_get_client):
        from src.server import plan_fixture_swap

        mock_get_client.return_value = _client(
            "cd /", _fixture_listing(OLD_TYPE), _info(1, "Dimmer", "Pan"), "cd /",
            "cd /", _fixture_listing(OLD_TYPE), "cd /",
        )

        data = json.loads(
            await plan_fixture_swap(old_fixture_type=OLD_TYPE, new_fixture_type=NEW_TYPE)
        )

        assert data["risk_level"] is None
        assert data["compatibility_percent"] is None
        assert data["new_type_status"] == "not_found"
        assert "no compatibility to report" in data["error"]
        # the old type was fine, and that is reported
        assert data["old_type_status"] == "ok"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_old_type_not_patched(self, mock_get_client):
        from src.server import plan_fixture_swap

        mock_get_client.return_value = _client(
            "cd /", _fixture_listing(NEW_TYPE), "cd /",
            "cd /", _fixture_listing(NEW_TYPE), _info(1, "Dimmer"), "cd /",
        )

        data = json.loads(
            await plan_fixture_swap(old_fixture_type=OLD_TYPE, new_fixture_type=NEW_TYPE)
        )

        assert data["risk_level"] is None
        assert data["old_type_status"] == "not_found"
        assert data["new_type_status"] == "ok"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fixture_info_rejected(self, mock_get_client):
        from src.server import plan_fixture_swap

        mock_get_client.return_value = _client(
            "cd /", _fixture_listing(OLD_TYPE, NEW_TYPE),
            "Executing : Info fixture 1\n\r\r Error #66: CANNOT ASSIGN\n\r\r [Fixture]>",
            "cd /",
            "cd /", _fixture_listing(OLD_TYPE, NEW_TYPE), _info(2, "Dimmer"), "cd /",
        )

        data = json.loads(
            await plan_fixture_swap(old_fixture_type=OLD_TYPE, new_fixture_type=NEW_TYPE)
        )

        assert data["risk_level"] is None
        assert data["old_type_status"] == "unreadable"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fixture_info_returns_nothing(self, mock_get_client):
        """A fixture that answers with no attributes is not a readable type."""
        from src.server import plan_fixture_swap

        mock_get_client.return_value = _client(
            "cd /", _fixture_listing(OLD_TYPE),
            "Executing : Info fixture 1\n\r\r [Fixture]>",
            "cd /",
            "cd /", _fixture_listing(OLD_TYPE), "cd /",
        )

        data = json.loads(
            await plan_fixture_swap(old_fixture_type=OLD_TYPE, new_fixture_type=NEW_TYPE)
        )

        assert data["old_type_status"] == "unreadable"
        assert data["risk_level"] is None

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_empty_fixture_listing(self, mock_get_client):
        from src.server import plan_fixture_swap

        mock_get_client.return_value = _client(
            "cd /", "WARNING, NO OBJECTS FOUND FOR LIST\n\r\r [Fixture]>", "cd /",
            "cd /", "WARNING, NO OBJECTS FOUND FOR LIST\n\r\r [Fixture]>", "cd /",
        )

        data = json.loads(
            await plan_fixture_swap(old_fixture_type=OLD_TYPE, new_fixture_type=NEW_TYPE)
        )

        assert data["old_type_status"] == "not_found"
        assert data["new_type_status"] == "not_found"
        assert data["risk_level"] is None

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_navigation_is_restored_after_a_failed_lookup(self, mock_get_client):
        """A not-found type must still leave the console at the root.

        The lookup runs twice and the second one starts with cd /, but leaving
        the cd tree dirty would corrupt whatever reads next.
        """
        from src.server import plan_fixture_swap

        mock_get_client.return_value = _client(
            "cd /", _fixture_listing(OLD_TYPE), _info(1, "Dimmer"), "cd /",
            "cd /", _fixture_listing(OLD_TYPE), "cd /",
        )

        await plan_fixture_swap(old_fixture_type=OLD_TYPE, new_fixture_type=NEW_TYPE)

        sent = [c.args[0] for c in mock_get_client.return_value.send_command_with_response.call_args_list]
        assert sent[0] == "cd /"
        assert sent[-1] == "cd /"
        # one cd / before and after each of the two lookups
        assert sent.count("cd /") == 4
