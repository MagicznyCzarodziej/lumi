"""Episode neighbor lookup tests."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.domain.library.episode_navigation import find_episode_display_name, find_episode_neighbors
from tests.constants import MOCK_LIBRARY_ROOT


def _load_entries():
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    return container.library_repository.get_top_level_entries()


def test_first_episode_has_next_only() -> None:
    entries = _load_entries()
    path = PurePosixPath("Band of Brothers/Season 1/S01E01.mkv")
    neighbors = find_episode_neighbors(entries, path)
    assert neighbors.previous is None
    assert neighbors.next == PurePosixPath("Band of Brothers/Season 1/S01E02.mkv")


def test_middle_episode_has_both_neighbors() -> None:
    entries = _load_entries()
    path = PurePosixPath("Band of Brothers/Season 1/S01E02.mkv")
    neighbors = find_episode_neighbors(entries, path)
    assert neighbors.previous == PurePosixPath("Band of Brothers/Season 1/S01E01.mkv")
    assert neighbors.next == PurePosixPath("Band of Brothers/Season 1/S01E03.mkv")


def test_non_episode_returns_no_neighbors() -> None:
    entries = _load_entries()
    neighbors = find_episode_neighbors(entries, PurePosixPath("12 Angry Men/12 Angry Men.mp4"))
    assert neighbors.previous is None
    assert neighbors.next is None


def test_find_episode_display_name() -> None:
    entries = _load_entries()
    name = find_episode_display_name(entries, PurePosixPath("Band of Brothers/Season 1/S01E02.mkv"))
    assert name == "S01E02"


def test_non_episode_has_no_display_name() -> None:
    entries = _load_entries()
    assert find_episode_display_name(entries, PurePosixPath("12 Angry Men/12 Angry Men.mp4")) is None


def test_matches_library_root_prefixed_path() -> None:
    entries = _load_entries()
    path = MOCK_LIBRARY_ROOT / "Band of Brothers/Season 1/S01E02.mkv"
    neighbors = find_episode_neighbors(entries, path)
    assert neighbors.previous == PurePosixPath("Band of Brothers/Season 1/S01E01.mkv")
    assert neighbors.next == PurePosixPath("Band of Brothers/Season 1/S01E03.mkv")
