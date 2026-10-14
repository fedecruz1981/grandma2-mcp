"""Los parsers contra respuestas REALES de grandMA2.

Los tests de este repo se escribieron con respuestas inventadas ("1  Cue1")
que no coinciden con lo que manda la consola. La fila real de un pool listing
arranca con el prefijo del tipo:

    Sequ   1 1    ...
    Macro 1 1    ...
    Cue 1 1       ...
    Fixture 1 1   ...

Con el parser anterior (^\\s*(\\d+)\\s) eso no matchea ni una fila: sobre el
show de prueba, 0 de 165 secuencias y 0 de 6 macros.

Las capturas viven en tests/fixtures/ma2_replies.py, con el ANSI tal cual.
"""

import pytest

from src.cue_reads import cue_ids_in, object_ids_in
from tests.fixtures.ma2_replies import (
    LIST_CUE_ONE,
    LIST_CUE_SEQUENCE,
    LIST_CUE_SEQUENCE_MULTI,
    LIST_FIXTURE,
    LIST_MACRO,
    LIST_PRESET_POOL,
    LIST_SEQUENCE,
    NO_OBJECTS,
)


class TestRowPrefixIsReal:
    """El prefijo del tipo está en cada fila de un listado real."""

    def test_sequence_rows_start_with_sequ(self):
        # "Sequ" also appears in the Track column, so count rows, not substrings.
        filas = [ln for ln in LIST_SEQUENCE.splitlines() if ln.strip().startswith("Sequ ")]
        assert len(filas) == 3

    def test_macro_rows_start_with_macro(self):
        filas = [ln for ln in LIST_MACRO.splitlines() if ln.strip().startswith("Macro ")]
        assert len(filas) == 3

    def test_cue_rows_start_with_cue(self):
        assert any(ln.strip().startswith("Cue 1") for ln in LIST_CUE_SEQUENCE.splitlines())

    def test_fixture_rows_start_with_fixture(self):
        assert any(
            ln.strip().startswith("Fixture 1") for ln in LIST_FIXTURE.splitlines()
        )


class TestCueIdsInOnRealReplies:
    def test_real_single_cue_listing(self):
        # Antes devolvía []
        assert cue_ids_in(LIST_CUE_SEQUENCE, 10) == ["1"]

    def test_real_multi_cue_listing(self):
        assert cue_ids_in(LIST_CUE_SEQUENCE_MULTI, 10) == ["1", "2", "3.1", "10"]

    def test_sub_cue_keeps_its_decimal(self):
        assert cue_ids_in(LIST_CUE_SEQUENCE_MULTI, 10)[2] == "3.1"

    def test_ten_does_not_become_one_point_zero(self):
        ids = cue_ids_in(LIST_CUE_SEQUENCE_MULTI, 10)
        assert "10" in ids
        assert "10.0" not in ids

    def test_header_row_is_not_mistaken_for_data(self):
        # "      Number  MIB  Trig ..." empieza con una palabra, no con un número
        assert "Number" not in cue_ids_in(LIST_CUE_SEQUENCE, 10)

    def test_empty_listing(self):
        assert cue_ids_in(NO_OBJECTS, 10) == []

    def test_limit_still_applies(self):
        assert cue_ids_in(LIST_CUE_SEQUENCE_MULTI, 2) == ["1", "2"]


class TestObjectIdsInOnRealReplies:
    """El mismo parser, para cualquier objeto del pool."""

    @pytest.mark.parametrize(
        ("reply", "expected"),
        [
            (LIST_SEQUENCE, ["1", "2", "3"]),
            (LIST_MACRO, ["1", "2", "3"]),
            (LIST_FIXTURE, ["1", "2"]),
            (LIST_CUE_SEQUENCE, ["1"]),
        ],
    )
    def test_prefixed_rows_yield_ids(self, reply, expected):
        assert object_ids_in(reply, 10) == expected

    def test_preset_pool_uses_the_type_prefix_too(self):
        # "Beam 5.1 5.1  SN FROST" — el prefijo es el nombre del preset type
        assert object_ids_in(LIST_PRESET_POOL, 10) == ["5.1"]

    def test_limit(self):
        assert object_ids_in(LIST_SEQUENCE, 2) == ["1", "2"]

    def test_empty_listing(self):
        assert object_ids_in(NO_OBJECTS, 10) == []


class TestBareNumberRowsStillWork:
    """Lo que escriben los tests viejos, y lo que devuelve info/preset sin tipo."""

    def test_bare_number(self):
        assert object_ids_in("1  A\n2  B\n3  C\n", 10) == ["1", "2", "3"]

    def test_bare_number_sub_cue(self):
        assert object_ids_in("1  A\n1.1  B\n2  C\n", 10) == ["1", "1.1", "2"]

    def test_mixed_prefixed_and_bare(self):
        assert object_ids_in("Sequ 1 x\n2 y\nCue 3 z\n", 10) == ["1", "2", "3"]


class TestHeadersAndNoiseAreNotData:
    @pytest.mark.parametrize(
        "line",
        [
            "      Number  MIB  Trig  TrigTime  Mode",
            "         No.  Name      Special  Info",
            "                   LibraryName             ScreenName",
            "Executing : List Cue 1 Sequence 156",
            " [Macro]>\x1b[K",
            "",
        ],
    )
    def test_noise_yields_nothing(self, line):
        assert object_ids_in(line, 10) == []


class TestWhatCueListingActuallyContains:
    """Documenta lo que 'list cue' devuelve: la fila, no los valores.

    Verificado en vivo el 2026-10-14 contra 3.9.60.82. Una herramienta que
    pretenda comparar el CONTENIDO de dos cues tiene que entrar al cue con
    'cd Sequence N Cue M' + 'list'; 'list cue' solo da trig/modo/loop/tiempos.
    """

    def test_cue_listing_has_trigger_and_mode_not_channel_values(self):
        # The column names live in the header row; the data row carries the
        # values: trigger "*", mode "Go", loop "None"/"Infinite".
        lineas = [ln for ln in LIST_CUE_ONE.splitlines() if ln.strip()]
        cabecera = next(ln for ln in lineas if "Number" in ln)
        fila = next(ln for ln in lineas if ln.strip().startswith("Cue 1"))
        assert "Trig" in cabecera and "Mode" in cabecera
        for valor in ("*", "Go", "Normal", "Infinite"):
            assert valor in fila
        # No channel values of the Dimmer= / Color= shape
        assert "Dimmer" not in fila
        assert "Color" not in fila

    def test_no_ansi_escapes_reach_the_extracted_ids(self):
        for i in cue_ids_in(LIST_CUE_SEQUENCE, 10):
            assert "\x1b" not in i
