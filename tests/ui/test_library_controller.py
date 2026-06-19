"""Library controller tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import PurePosixPath

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.domain.library.models import EntryId, Series, StandaloneFilm
from lumi.infrastructure.mock.mock_video_player import MockVideoPlayer
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.router import Router
from lumi.ui.screens.library.controller import (
    EntriesFilter,
    active_letter_for_row,
    build_alphabet_symbols,
    build_library_ui_state,
    collect_tags,
    find_entry_index_for_letter,
    matches_entries_filter,
    matches_search_query,
    matches_tag_filter,
    on_library_entry_clicked,
)
from PySide6.QtWidgets import QApplication, QStackedWidget


def _load_mock_container():
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    return container


def test_collect_tags_from_mock_library() -> None:
    container = _load_mock_container()
    tags = collect_tags(container.library_repository.get_top_level_entries())
    assert tags
    assert tags == sorted(tags)
    assert all(tag == tag.lower() for tag in tags)


def test_entries_filter_films_excludes_pure_series() -> None:
    container = _load_mock_container()
    entries = container.library_repository.get_top_level_entries()
    series_only = [entry for entry in entries if isinstance(entry, Series)]
    assert series_only
    assert all(not matches_entries_filter(entry, EntriesFilter.FILMS) for entry in series_only)


def test_tag_filter_is_case_insensitive() -> None:
    container = _load_mock_container()
    entries = container.library_repository.get_top_level_entries()
    tagged = next(entry for entry in entries if matches_tag_filter(entry, next(iter(entry.tags)).lower()))
    tag = next(iter(tagged.tags)).lower()
    assert matches_tag_filter(tagged, tag)


def test_matches_search_query_matches_title_and_tags() -> None:
    from lumi.domain.library.models import Name

    film = StandaloneFilm(
        id=EntryId(id="1"),
        name=Name(name="12 Angry Men"),
        root_relative_path=MOCK_LIBRARY_ROOT / "12 Angry Men",
        root_relative_poster_path=MOCK_LIBRARY_ROOT / "12 Angry Men/poster.jpg",
        tags=frozenset({"classic"}),
        franchise=None,
        video_files=[],
    )
    assert matches_search_query(film, "angry")
    assert matches_search_query(film, "classic")
    assert not matches_search_query(film, "batman")


def test_build_library_ui_state_filters_by_search() -> None:
    QApplication.instance() or QApplication([])
    container = _load_mock_container()
    context = ScreenContext(container.library_repository, MockVideoPlayer())
    stack = QStackedWidget()
    router = Router(stack, context)
    focused: list[PurePosixPath | None] = []

    state = build_library_ui_state(
        container.library_repository.get_top_level_entries(),
        entries_filter=EntriesFilter.ALL,
        tag_filter=None,
        router=router,
        video_player=context.video_player,
        on_entry_focus=lambda entry: focused.append(entry.root_relative_poster_path),
    )

    assert state.entries
    assert not state.is_loading
    symbols = build_alphabet_symbols(state.entries)
    assert symbols[0] == "#"
    assert "B" in symbols
    assert find_entry_index_for_letter(state.entries, "#") == 0

    filtered = build_library_ui_state(
        container.library_repository.get_top_level_entries(),
        entries_filter=EntriesFilter.ALL,
        tag_filter=None,
        search_query="alien",
        router=router,
        video_player=context.video_player,
        on_entry_focus=lambda entry: None,
    )
    assert filtered.entries
    assert all("alien" in model.name.name.lower() for model in filtered.entries)


def test_active_letter_maps_digits_to_hash() -> None:
    from lumi.domain.library.models import Name
    from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel

    entries = [
        ListEntryUiModel(
            name=Name(name="12 Angry Men"),
            entry_type=ListEntryType.single(),
            poster_path=None,
            on_click=lambda: None,
            on_focus=lambda: None,
        ),
    ]
    assert active_letter_for_row(entries, 0) == "#"
    assert active_letter_for_row(
        [
            ListEntryUiModel(
                name=Name(name="Ace Ventura"),
                entry_type=ListEntryType.single(),
                poster_path=None,
                on_click=lambda: None,
                on_focus=lambda: None,
            ),
        ],
        0,
    ) == "A"


def test_standalone_film_click_plays_video(monkeypatch) -> None:
    QApplication.instance() or QApplication([])
    container = _load_mock_container()
    context = ScreenContext(container.library_repository, MockVideoPlayer())
    stack = QStackedWidget()
    router = Router(stack, context)
    played: list[PurePosixPath] = []

    def fake_play(path: PurePosixPath) -> None:
        played.append(path)

    monkeypatch.setattr(context.video_player, "play_video", fake_play)

    entries = container.library_repository.get_top_level_entries()
    film = next(entry for entry in entries if isinstance(entry, StandaloneFilm))
    on_library_entry_clicked(film, router, context.video_player)
    assert played
