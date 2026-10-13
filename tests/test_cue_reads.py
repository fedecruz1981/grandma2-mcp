"""Tests for src/cue_reads.py — typed console reads."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cue_reads import (
    classify,
    cue_ids_in,
    cue_number,
    list_cues,
    read_cue,
    read_object,
    sequence_suffix,
    strip_chrome,
)


def _client(*replies: str) -> MagicMock:
    client = MagicMock()
    client.send_command_with_response = AsyncMock(side_effect=list(replies))
    return client


# Real onPC 3.9.60.50 reply shapes (live-verified 2026-10-08).
REPLY_NO_OBJECTS = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mcue\x1b[37m 3 sequence 156\n"
    "\r\r WARNING, NO OBJECTS FOUND FOR LIST\n\r\r [Fixture]>\x1b[K"
)
REPLY_WITH_DATA = (
    "Executing : \x1b[32mList\x1b[37m \x1b[32mcue\x1b[37m 3 sequence 156\n"
    "\r\r Dimmer 100\n\r\r Color Red\n\r\r [Fixture]>\x1b[K"
)
REPLY_ERROR = (
    "Executing : \x1b[32mGoto\x1b[37m cue 9 sequence 156\n"
    "\r\r Error #72: COMMAND NOT EXECUTED\n\r\r [Fixture]>\x1b[K"
)


class TestCueNumber:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (3, "3"),
            (3.0, "3"),
            (12.0, "12"),
            (1.1, "1.1"),
            ("7", "7"),
            ("1.1", "1.1"),
        ],
    )
    def test_spellings(self, value, expected):
        assert cue_number(value) == expected

    def test_a_whole_cue_never_gains_a_decimal(self):
        for value in (1, 5, 40, 161):
            assert "." not in cue_number(float(value))

    def test_sub_cue_keeps_its_decimal(self):
        assert cue_number(1.1) == "1.1"
        assert cue_number(10.25) == "10.25"


class TestSequenceSuffix:
    def test_present(self):
        assert sequence_suffix(156) == " sequence 156"

    def test_absent(self):
        assert sequence_suffix(None) == ""


class TestStripChrome:
    def test_drops_the_command_echo(self):
        assert strip_chrome(REPLY_WITH_DATA) == ["Dimmer 100", "Color Red"]

    def test_drops_the_prompt(self):
        assert all(not line.endswith(">") for line in strip_chrome(REPLY_WITH_DATA))

    def test_drops_the_refusal(self):
        assert strip_chrome(REPLY_NO_OBJECTS) == []

    def test_drops_ansi_only_lines(self):
        assert strip_chrome("\x1b[32m\x1b[37m\n\r\r Dimmer 100\n") == ["Dimmer 100"]

    def test_keeps_a_value_that_merely_starts_like_an_error(self):
        assert strip_chrome("Error 66 hand mode\n") == ["Error 66 hand mode"]

    def test_empty_reply(self):
        assert strip_chrome("") == []


class TestClassify:
    def test_data_is_found_and_usable(self):
        read = classify(REPLY_WITH_DATA, "list cue 3 sequence 156")
        assert read.found is True
        assert read.usable is True
        assert read.rejected is False
        assert read.lines == ["Dimmer 100", "Color Red"]
        assert read.command == "list cue 3 sequence 156"

    def test_no_objects_is_not_found(self):
        read = classify(REPLY_NO_OBJECTS)
        assert read.found is False
        assert read.usable is False
        assert read.lines == []

    def test_bare_no_objects_also_counts(self):
        assert classify("NO OBJECTS FOUND").found is False

    def test_lowercase_also_counts(self):
        assert classify("no objects found").found is False

    def test_error_is_reported_with_its_code(self):
        read = classify(REPLY_ERROR)
        assert read.rejected is True
        assert read.error_code == 72
        assert read.error_text == "COMMAND NOT EXECUTED"

    def test_an_error_is_never_usable(self):
        read = classify(REPLY_ERROR)
        assert read.usable is False

    def test_empty_reply_is_not_found(self):
        # Nothing arrived, which is not the console confirming an empty object.
        read = classify("")
        assert read.found is False
        assert read.usable is False
        assert read.lines == []

    def test_whitespace_only_reply_is_not_found(self):
        assert classify("\r\r  \n").found is False

    def test_a_cue_that_exists_but_is_empty_is_still_found(self):
        # The console echoed the command and printed its prompt, with no data
        # rows. That is an existing cue that lists nothing — not a failed read —
        # so found stays True. There is no way to tell this apart from "the cue
        # exists and happens to be empty", and found=True is the right answer
        # for both.
        read = classify("Executing : List cue 3\n\r\r [Fixture]>\x1b[K")
        assert read.found is True
        assert read.lines == []

    def test_found_with_no_data_lines_is_not_usable_for_parsing(self):
        # usable answers "did the read succeed"; the caller that needs content
        # must check lines, because a valid cue can legitimately be empty.
        read = classify("Executing : List cue 3\n\r\r [Fixture]>\x1b[K")
        assert read.usable is True
        assert not read.lines

    def test_object_read_is_frozen(self):
        import dataclasses

        read = classify(REPLY_WITH_DATA)
        with pytest.raises(dataclasses.FrozenInstanceError):
            read.found = False


class TestReadObject:
    @pytest.mark.asyncio
    async def test_builds_the_expected_command(self):
        client = _client(REPLY_WITH_DATA)
        await read_object(client, "cue", 3, sequence=156)
        assert client.send_command_with_response.call_args_list[0].args[0] == (
            "list cue 3 sequence 156"
        )

    @pytest.mark.asyncio
    async def test_whole_cue_from_a_float_loses_the_decimal(self):
        client = _client(REPLY_WITH_DATA, REPLY_WITH_DATA)
        await read_object(client, "cue", 3.0, sequence=156)
        await read_object(client, "cue", 4.0, sequence=156)
        asked = [c.args[0] for c in client.send_command_with_response.call_args_list]
        assert asked == ["list cue 3 sequence 156", "list cue 4 sequence 156"]

    @pytest.mark.asyncio
    async def test_no_sequence_qualifier(self):
        client = _client(REPLY_WITH_DATA)
        await read_object(client, "fixture", 5)
        assert client.send_command_with_response.call_args_list[0].args[0] == "list fixture 5"

    @pytest.mark.asyncio
    async def test_non_cue_types_keep_their_number_verbatim(self):
        client = _client(REPLY_WITH_DATA)
        await read_object(client, "group", 3.0)
        assert client.send_command_with_response.call_args_list[0].args[0] == "list group 3.0"

    @pytest.mark.asyncio
    async def test_none_sends_nothing(self):
        client = _client()
        read = await read_object(client, "cue", None)
        assert read.found is False
        client.send_command_with_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_result_carries_the_command(self):
        client = _client(REPLY_WITH_DATA)
        read = await read_object(client, "cue", 3, sequence=156)
        assert read.command == "list cue 3 sequence 156"

    @pytest.mark.asyncio
    async def test_custom_echo_command_is_recorded(self):
        client = _client(REPLY_WITH_DATA)
        read = await read_object(client, "cue", 3, echo_command="List Cue Sequence 156")
        assert read.command == "List Cue Sequence 156"


class TestReadCue:
    @pytest.mark.asyncio
    async def test_command_shape(self):
        client = _client(REPLY_WITH_DATA)
        await read_cue(client, 156, 3.0)
        assert client.send_command_with_response.call_args_list[0].args[0] == (
            "list cue 3 sequence 156"
        )

    @pytest.mark.asyncio
    async def test_missing_cue_is_reported_as_not_found(self):
        client = _client(REPLY_NO_OBJECTS)
        read = await read_cue(client, 156, 3)
        assert read.found is False
        assert read.usable is False


class TestListCues:
    @pytest.mark.asyncio
    async def test_command_shape(self):
        client = _client("1  A\n2  B\n")
        await list_cues(client, 156)
        assert client.send_command_with_response.call_args_list[0].args[0] == (
            "list cue sequence 156"
        )

    @pytest.mark.asyncio
    async def test_empty_sequence_is_not_found(self):
        client = _client(REPLY_NO_OBJECTS)
        read = await list_cues(client, 99)
        assert read.found is False


class TestCueIdsIn:
    def test_deduplicates(self):
        assert cue_ids_in("1 A\n1 A again\n2 B\n", 10) == ["1", "2"]

    def test_keeps_sub_cues(self):
        assert cue_ids_in("1 A\n1.1 B\n2 C\n", 10) == ["1", "1.1", "2"]

    def test_respects_the_limit(self):
        assert cue_ids_in("1 A\n2 B\n3 C\n4 D\n", 2) == ["1", "2"]

    def test_empty_listing(self):
        assert cue_ids_in("NO OBJECTS FOUND", 10) == []

    def test_none_handled(self):
        assert cue_ids_in("", 10) == []


class TestTheBugThisExistsFor:
    """Two missing cues must not read as two identical cues.

    Before the typed read, `diff_cues` compared the two "NO OBJECTS FOUND"
    replies, found no differing lines, and reported identical=true over two
    cues that do not exist.
    """

    @pytest.mark.asyncio
    async def test_both_cues_missing(self):
        client = _client(REPLY_NO_OBJECTS, REPLY_NO_OBJECTS)
        a = await read_cue(client, 156, 3)
        b = await read_cue(client, 156, 4)
        assert a.found is False and b.found is False
        assert a.raw == b.raw  # the replies really are identical ...
        assert a.usable is False and b.usable is False  # ... and neither is usable

    @pytest.mark.asyncio
    async def test_data_lines_differ_only_when_the_cues_differ(self):
        client = _client(
            "Executing : List cue 1 sequence 1\n\r\r Dimmer 100\n\r\r [Fixture]>",
            "Executing : List cue 2 sequence 1\n\r\r Dimmer 100\n\r\r [Fixture]>",
        )
        a = await read_cue(client, 1, 1)
        b = await read_cue(client, 1, 2)
        assert a.lines == b.lines == ["Dimmer 100"]
        assert set(a.lines) ^ set(b.lines) == set()  # identical bodies ...

        client2 = _client(
            "Executing : List cue 1 sequence 1\n\r\r Dimmer 100\n\r\r [Fixture]>",
            "Executing : List cue 2 sequence 1\n\r\r Dimmer 50\n\r\r [Fixture]>",
        )
        c = await read_cue(client2, 1, 1)
        d = await read_cue(client2, 1, 2)
        assert set(c.lines) ^ set(d.lines) == {"Dimmer 100", "Dimmer 50"}
