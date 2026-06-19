"""Entry ordering normalization tests."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.library.entry_ordering import episodes_group_sort_key, normalize_library
from lumi.domain.library.models import EntryId, EpisodesGroup, Episode, Name, Series


def test_normalize_library_reorders_cached_seasons_by_name_number() -> None:
    series = Series(
        id=EntryId(id="nge"),
        name=Name("Neon Genesis Evangelion"),
        root_relative_path=PurePosixPath("Neon Genesis Evangelion"),
        root_relative_poster_path=PurePosixPath("Neon Genesis Evangelion"),
        tags=frozenset(),
        franchise=None,
        seasons=[
            EpisodesGroup(
                id=EntryId(id="s3"),
                name=Name("03"),
                root_relative_path=PurePosixPath("Neon Genesis Evangelion/03"),
                root_relative_poster_path=PurePosixPath("Neon Genesis Evangelion"),
                ordinal_number=1,
                episodes=[],
            ),
            EpisodesGroup(
                id=EntryId(id="s1"),
                name=Name("01"),
                root_relative_path=PurePosixPath("Neon Genesis Evangelion/01"),
                root_relative_poster_path=PurePosixPath("Neon Genesis Evangelion"),
                ordinal_number=2,
                episodes=[],
            ),
            EpisodesGroup(
                id=EntryId(id="s2"),
                name=Name("02"),
                root_relative_path=PurePosixPath("Neon Genesis Evangelion/02"),
                root_relative_poster_path=PurePosixPath("Neon Genesis Evangelion"),
                ordinal_number=3,
                episodes=[],
            ),
        ],
    )

    normalized = normalize_library([series])[0]
    assert isinstance(normalized, Series)
    assert [season.name.name for season in normalized.seasons] == ["01", "02", "03"]


def test_episodes_group_sort_key_uses_folder_name_over_stale_ordinal() -> None:
    stale = EpisodesGroup(
        id=EntryId(id="s3"),
        name=Name("03"),
        root_relative_path=PurePosixPath("Series/03"),
        root_relative_poster_path=PurePosixPath("Series"),
        ordinal_number=1,
        episodes=[],
    )
    assert episodes_group_sort_key(stale)[0] == 3
