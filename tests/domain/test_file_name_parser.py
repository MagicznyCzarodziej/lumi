"""FileNameParser tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from lumi.domain.library.building import file_name_parser as parser


@dataclass(frozen=True)
class EpisodeTestData:
    file_name: str
    extensions: set[str]
    series_name: str
    expected_title: str


@pytest.mark.parametrize(
    "test_data",
    [
        EpisodeTestData(
            "Some series - S02E01 - Title.mkv",
            {"mkv"},
            "Some series",
            "S02E01 - Title",
        ),
        EpisodeTestData(
            "Some series - s02e01 - Title.mkv",
            {"mkv"},
            "Some series",
            "s02e01 - Title",
        ),
        EpisodeTestData(
            "Some series - S02E01 - Title.mkv",
            set(),
            "Some series",
            "S02E01 - Title",
        ),
    ],
)
def test_parse_episode_details_valid(test_data: EpisodeTestData) -> None:
    details = parser.parse_episode_details(
        file_name=test_data.file_name,
        video_extensions=test_data.extensions,
        series_name=test_data.series_name,
    )
    assert details.title == test_data.expected_title
    assert details.number == 1


@pytest.mark.parametrize(
    "test_data",
    [
        EpisodeTestData(
            "Series title - S03ES2 - Episode title.mkv",
            {"mkv"},
            "Series title",
            "S03ES2 - Episode title",
        ),
        EpisodeTestData(
            "Series title - Episode title.mkv",
            {"mkv"},
            "Series title",
            "Episode title",
        ),
        EpisodeTestData(
            "Episode title.mkv",
            {"mkv"},
            "Series title",
            "Episode title",
        ),
    ],
)
def test_parse_episode_details_fallback(test_data: EpisodeTestData) -> None:
    details = parser.parse_episode_details(
        file_name=test_data.file_name,
        video_extensions=test_data.extensions,
        series_name=test_data.series_name,
    )
    assert details.title == test_data.expected_title
    assert details.number == -1


@pytest.mark.parametrize(
    "folder_name",
    [
        "Main name (Alternative name)",
        "Main name    (Alternative name)   ",
        "[12] Main name (Alternative name)",
    ],
)
def test_parse_name_with_alternative_name(folder_name: str) -> None:
    result = parser.parse_name(folder_name)
    assert result.name == "Main name"
    assert result.alternative_name == "Alternative name"


@pytest.mark.parametrize(
    "folder_name",
    [
        "Main name",
        "Main name    ",
        "[12] Main name",
    ],
)
def test_parse_name_without_alternative_name(folder_name: str) -> None:
    result = parser.parse_name(folder_name)
    assert result.name == "Main name"
    assert result.alternative_name is None


def test_extract_season_number_from_episode() -> None:
    assert (
        parser.extract_season_number_from_episode("Series title - S01E02 - Episode title.mkv")
        == 1
    )


def test_extract_season_number_from_episode_invalid() -> None:
    assert (
        parser.extract_season_number_from_episode("Series title - S01ES1 - Episode title.mkv")
        is None
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Season 01", 1),
        ("S11", 11),
        ("01", 1),
        ("[01] Season", 1),
        ("[11] Season", 11),
        ("01 - Title", 1),
    ],
)
def test_extract_season_number(name: str, expected: int) -> None:
    assert parser.extract_season_number(name) == expected


def test_parse_episode_details_dash_number() -> None:
    details = parser.parse_episode_details(
        file_name="Neon Genesis Evangelion - 03 - Angel Attack.mkv",
        video_extensions={"mkv"},
        series_name="Neon Genesis Evangelion",
    )
    assert details.number == 3
    assert details.title == "03 - Angel Attack"


def test_parse_episode_details_bracket_number() -> None:
    details = parser.parse_episode_details(
        file_name="[03] Angel Attack.mkv",
        video_extensions={"mkv"},
        series_name="Neon Genesis Evangelion",
    )
    assert details.number == 3
    assert details.title == "[03] Angel Attack"


def test_get_ordinal_number_from_name() -> None:
    assert parser.get_ordinal_number_from_name("[1] Title") == 1


@pytest.mark.parametrize(
    "text",
    ["(1) Title", "1 Title", "Title"],
)
def test_get_ordinal_number_from_name_invalid(text: str) -> None:
    assert parser.get_ordinal_number_from_name(text) is None
