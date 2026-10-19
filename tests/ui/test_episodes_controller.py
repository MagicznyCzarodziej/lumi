"""Episodes controller tests."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.library.models import EntryId, Episode, EpisodesGroup, Name, Series
from lumi.ui.navigation.destinations import EpisodesGroupDestination
from lumi.ui.screens.episodes.controller import build_episodes_state


class _Repository:
    def __init__(self, entries: list[Series]) -> None:
        self._entries = entries

    def get_top_level_entries(self) -> list[Series]:
        return self._entries


class _VideoPlayer:
    def __init__(self) -> None:
        self.played_paths: list[PurePosixPath] = []

    def play_video(self, absolute_path: PurePosixPath) -> None:
        self.played_paths.append(absolute_path)


def test_episode_state_shows_alternative_season_title_and_plays_episode() -> None:
    episode = Episode(
        id=EntryId("episode-1"),
        name=Name("Episode 1"),
        root_relative_path=PurePosixPath("series/season-1/episode-1.mkv"),
        ordinal_number=1,
    )
    season = EpisodesGroup(
        id=EntryId("season-1"),
        name=Name("Season 1", alternative_name="First season"),
        root_relative_path=PurePosixPath("series/season-1"),
        root_relative_poster_path=PurePosixPath("series/season-1"),
        ordinal_number=1,
        episodes=[episode],
    )
    series = Series(
        id=EntryId("series"),
        name=Name("Series"),
        root_relative_path=PurePosixPath("series"),
        root_relative_poster_path=PurePosixPath("series"),
        tags=frozenset({"drama"}),
        franchise=None,
        seasons=[season],
    )
    player = _VideoPlayer()

    state = build_episodes_state(
        EpisodesGroupDestination(episodes_group_id="season-1"),
        _Repository([series]),
        player,
    )

    assert state is not None
    assert state.breadcrumbs == "Library / Series"
    assert state.title == "Season 1"
    assert state.subtitle == "First season"
    assert state.tags == frozenset({"drama"})

    state.entries[0].on_click()
    assert player.played_paths == [PurePosixPath("series/season-1/episode-1.mkv")]
