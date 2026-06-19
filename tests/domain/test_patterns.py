"""Patterns tests."""

from __future__ import annotations

import pytest

from lumi.domain.library.building.patterns import (
    EPISODE_FILE_PATTERN,
    NAME_WITH_ALTERNATIVE_NAME_PATTERN,
    ORDINAL_NUMBER_PATTERN,
    SEASON_NUMBER_PATTERN,
)


@pytest.mark.parametrize(
    "file_name",
    ["[1] ", "[1234] ", "[01] "],
)
def test_ordinal_number_pattern_valid(file_name: str) -> None:
    assert ORDINAL_NUMBER_PATTERN.matches_text_exactly(file_name) is True


@pytest.mark.parametrize(
    "file_name",
    [" [1] ", "(1) ", "1 "],
)
def test_ordinal_number_pattern_invalid(file_name: str) -> None:
    assert ORDINAL_NUMBER_PATTERN.matches_text_exactly(file_name) is False


@pytest.mark.parametrize(
    "text",
    ["Season 01", "Season 1", "season 1", "S01", "S1", "s1", "01", "1"],
)
def test_season_number_pattern_valid(text: str) -> None:
    assert SEASON_NUMBER_PATTERN.matches_text_exactly(text) is True


@pytest.mark.parametrize(
    "file_name",
    [
        "Series title - S01E02 - Episode title.mkv",
        "Series title - s01e02 - Episode title.MKV",
        "Series title - S01E02.mkv",
    ],
)
def test_episode_file_pattern_valid(file_name: str) -> None:
    assert EPISODE_FILE_PATTERN.matches_text_exactly(file_name) is True
    matcher = EPISODE_FILE_PATTERN.matches(file_name)
    assert matcher.matches()
    assert matcher.group("seasonNumber") == "01"
    assert matcher.group("episodeNumber") == "02"


@pytest.mark.parametrize(
    "file_name",
    [
        "Main name (Alternative name)",
        "Main name     (Alternative name)    ",
    ],
)
def test_name_with_alternative_name_pattern_valid(file_name: str) -> None:
    assert NAME_WITH_ALTERNATIVE_NAME_PATTERN.matches_text_exactly(file_name) is True
    matcher = NAME_WITH_ALTERNATIVE_NAME_PATTERN.matches(file_name)
    assert matcher.matches()
    assert matcher.group("mainName") == "Main name"
    assert matcher.group("alternativeName") == "Alternative name"
