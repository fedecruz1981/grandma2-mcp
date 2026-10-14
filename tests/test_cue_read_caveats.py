"""Las cuatro herramientas que leen cues deben decir que no leen contenidos.

Verificado en vivo contra grandMA2 3.9.60.82, show "inti y luna oct2026",
secuencia 156, cue 1 con 749 valores grabados: nueve formas de comando
(list cue, cd+list, list preset, info, info attribute, pd, list pd...) no
devuelven valores de canal. Solo el export XML los tiene.

El riesgo no es que la herramienta falle: es que devuelva un informe que suena
completo sobre datos que nunca vio. Por eso el caveat va SIEMPRE, incluso
cuando el resultado sale limpio.
"""

import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cue_reads import CUE_READ_SEES_TABLE_ROW_ONLY

# Filas reales capturadas en vivo (ver tests/fixtures/ma2_replies.py).
CUE_ROW = "Cue 1 1       *    Go              Normal  None  Infinite  Infinite   (1)"
CUE_ROW_2 = "Cue 2 2       *    Go              Normal  None  Infinite  Infinite   (2)"
LISTING_HEADER = (
    "      Number  MIB  Trig  TrigTime  Mode    Loop  Lcount    Ltime     \r\n\r\n"
)
LISTING = f"Executing : List Cue Sequence 156\r\n\r\n{LISTING_HEADER}{CUE_ROW}\r\n\r\n [Macro]>\x1b[K"
# The same listing with two cues, which is what detect_tracking_leaks needs to
# have something to compare.
LISTING_TWO = (
    f"Executing : List Cue Sequence 156\r\n\r\n{LISTING_HEADER}"
    f"{CUE_ROW}\r\n\r\n{CUE_ROW_2}\r\n\r\n [Macro]>\x1b[K"
)
ONE_CUE_BODY = f"{LISTING_HEADER}{CUE_ROW}\r\n\r\n [Macro]>\x1b[K"
TWO_CUE_BODY = f"{LISTING_HEADER}{CUE_ROW_2}\r\n\r\n [Macro]>\x1b[K"


def _client(
    cue_listing: str = LISTING,
    cue_body: str = ONE_CUE_BODY,
    sequence_listing: str | None = None,
) -> MagicMock:
    """A client that answers by command, not by call order.

    These tools loop over whatever the listing holds, so the number of reads
    depends on the fixture. Mapping on the command keeps each test about the
    answer instead of about how many times it gets asked.
    """
    client = MagicMock()

    def pick(cmd: str) -> str:
        low = cmd.strip().lower()
        if low == "list sequence" or low.startswith("list sequence "):
            return sequence_listing if sequence_listing is not None else cue_listing
        if re.match(r"^list cue \S+ sequence \S+$", low):
            return cue_body
        return cue_listing

    client.send_command_with_response = AsyncMock(side_effect=pick)
    return client


class TestTheConstantSaysWhatIsTrue:
    def test_it_names_the_row_not_the_values(self):
        assert "table row" in CUE_READ_SEES_TABLE_ROW_ONLY

    def test_it_points_at_the_xml(self):
        assert "XML" in CUE_READ_SEES_TABLE_ROW_ONLY

    def test_it_is_not_empty(self):
        assert len(CUE_READ_SEES_TABLE_ROW_ONLY) > 40


class TestDiffCues:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_result_carries_the_flag_and_caveat(self, mock_get_client):
        from src.server import diff_cues

        mock_get_client.return_value = _client(LISTING, ONE_CUE_BODY)

        data = json.loads(await diff_cues(sequence_id=156, cue_a=1, cue_b=2))

        assert data["cue_read_contents"] is False
        assert data["caveat"] == CUE_READ_SEES_TABLE_ROW_ONLY

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_flag_present_even_when_the_cues_match(self, mock_get_client):
        """A clean diff must still say it did not read contents."""
        from src.server import diff_cues

        mock_get_client.return_value = _client(LISTING, ONE_CUE_BODY)

        data = json.loads(await diff_cues(sequence_id=156, cue_a=1, cue_b=2))

        assert data["identical"] is True
        assert data["cue_read_contents"] is False


class TestDetectTrackingLeaks:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_clean_result_still_warns(self, mock_get_client):
        from src.server import detect_tracking_leaks

        mock_get_client.return_value = _client(LISTING_TWO, TWO_CUE_BODY)

        data = json.loads(await detect_tracking_leaks(sequence_id=156))

        assert data["cue_read_contents"] is False
        assert "never its channel values" in data["recommendation"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_the_wording_names_what_was_actually_compared(self, mock_get_client):
        """'No leaks detected' must not stand on its own."""
        from src.server import detect_tracking_leaks

        mock_get_client.return_value = _client(LISTING_TWO, TWO_CUE_BODY)

        data = json.loads(await detect_tracking_leaks(sequence_id=156))

        rec = data["recommendation"]
        assert "trigger/mode/loop rows match" in rec
        assert "not that no attribute value tracks forward" in rec


class TestCompareCueValues:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_result_carries_the_flag(self, mock_get_client):
        from src.server import compare_cue_values

        mock_get_client.return_value = _client(LISTING, ONE_CUE_BODY)

        data = json.loads(await compare_cue_values(sequence_id=156, cue_a=1, cue_b=2))

        assert data["cue_read_contents"] is False
        assert data["caveat"] == CUE_READ_SEES_TABLE_ROW_ONLY


class TestTraceAttributeLineage:
    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_empty_result_says_the_search_had_nothing_to_match(
        self, mock_get_client, mock_orch
    ):
        """The worst case: no hits, on a search that cannot find hits."""
        from src.server import trace_attribute_lineage

        snap = MagicMock()
        snap.executor_state = {}
        snap.active_macros = []
        snap.sequences = None
        snap.selected_fixture_count = 0
        snap.active_filter = None
        snap.active_world = None
        snap.console_modes = {}
        snap.selected_exec = ""
        snap.selected_exec_cue = ""
        mock_orch.last_snapshot = snap

        mock_get_client.return_value = _client(
            LISTING,
            sequence_listing="Sequ 1 1  Cue 1\r\nSequ 2 2  Cue 2\r\n [Macro]>\x1b[K",
        )

        data = json.loads(await trace_attribute_lineage(attribute="ColorRGB1"))

        assert data["candidate_sources"] == []
        assert data["cue_read_contents"] is False
        assert "not that no cue stores it" in data["summary"]

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_a_hit_is_still_flagged(self, mock_get_client, mock_orch):
        from src.server import trace_attribute_lineage

        snap = MagicMock()
        snap.executor_state = {}
        snap.active_macros = []
        snap.sequences = None
        snap.selected_fixture_count = 0
        snap.active_filter = None
        snap.active_world = None
        snap.console_modes = {}
        snap.selected_exec = ""
        snap.selected_exec_cue = ""
        mock_orch.last_snapshot = snap

        mock_get_client.return_value = _client(
            # The listing that names the attribute. This is the shape the tool
            # can actually find: a word in a listing, not a stored value.
            cue_body=(
                "      Number  MIB  Trig  TrigTime  Mode    Loop  Lcount    Ltime     \r\n\r\n"
                "Cue 1 1       *    Go   Dimmer 100   Normal  None  Infinite  Infinite   (1)"
                "\r\n\r\n [Macro]>\x1b[K"
            ),
            sequence_listing="Sequ 1 1  Cue 1\r\n [Macro]>\x1b[K",
        )

        data = json.loads(await trace_attribute_lineage(attribute="Dimmer"))

        assert data["candidate_sources"], data
        assert data["cue_read_contents"] is False
        # The summary must still carry the caveat even with a hit
        assert "never its channel values" in data["summary"]
