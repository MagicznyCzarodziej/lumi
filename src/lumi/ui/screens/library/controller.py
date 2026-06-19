"""Library screen controller."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from lumi.domain.library.models import (
    EpisodesGroup,
    FilmSeries,
    LibraryEntry,
    MediaGrouping,
    MediaGroupingFilm,
    Series,
    StandaloneFilm,
)
from lumi.domain.video_player import VideoPlayer
from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel
from lumi.ui.navigation.destinations import FilmSeriesDestination, MediaGroupingDestination, SeriesDestination
from lumi.ui.navigation.router import Router


class EntriesFilter(Enum):
    ALL = auto()
    FILMS = auto()
    SERIES = auto()


@dataclass(frozen=True)
class LibraryUiState:
    entries: list[ListEntryUiModel]
    tags: list[str]
    is_loading: bool = False


def collect_tags(entries: list[LibraryEntry]) -> list[str]:
    tags: set[str] = set()
    for entry in entries:
        tags.update(tag.lower() for tag in entry.tags)
    return sorted(tags)


def matches_entries_filter(entry: LibraryEntry, filter: EntriesFilter) -> bool:
    if filter is EntriesFilter.ALL:
        return True
    if filter is EntriesFilter.FILMS:
        return (
            isinstance(entry, StandaloneFilm)
            or isinstance(entry, FilmSeries)
            or (isinstance(entry, MediaGrouping) and any(isinstance(child, MediaGroupingFilm) for child in entry.entries))
        )
    if filter is EntriesFilter.SERIES:
        return (
            isinstance(entry, Series)
            or (isinstance(entry, MediaGrouping) and any(isinstance(child, EpisodesGroup) for child in entry.entries))
        )
    return True


def matches_tag_filter(entry: LibraryEntry, tag_filter: str | None) -> bool:
    if tag_filter is None:
        return True
    return tag_filter in {tag.lower() for tag in entry.tags}


def matches_search_query(entry: LibraryEntry, query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return True
    haystacks = [entry.name.name.lower(), entry.name.sort_name.lower()]
    if entry.name.alternative_name:
        haystacks.append(entry.name.alternative_name.lower())
    haystacks.extend(tag.lower() for tag in entry.tags)
    return any(normalized in hay for hay in haystacks)


def library_entry_type(entry: LibraryEntry) -> ListEntryType:
    if isinstance(entry, StandaloneFilm):
        return ListEntryType.single()
    if isinstance(entry, Series):
        return ListEntryType.series(len(entry.seasons))
    if isinstance(entry, MediaGrouping):
        return ListEntryType.grouping(len(entry.entries))
    if isinstance(entry, FilmSeries):
        return ListEntryType.playables_group(len(entry.films))
    raise TypeError(f"Unsupported library entry type: {type(entry)!r}")


def on_library_entry_clicked(entry: LibraryEntry, router: Router, video_player: VideoPlayer) -> None:
    if isinstance(entry, Series):
        router.push(SeriesDestination(series_id=entry.id.id))
    elif isinstance(entry, FilmSeries):
        router.push(FilmSeriesDestination(film_series_id=entry.id.id))
    elif isinstance(entry, MediaGrouping):
        router.push(MediaGroupingDestination(media_grouping_id=entry.id.id))
    elif isinstance(entry, StandaloneFilm) and entry.video_files:
        video_player.play_video(entry.video_files[0].absolute_path)


def build_library_ui_state(
    all_entries: list[LibraryEntry],
    *,
    entries_filter: EntriesFilter,
    tag_filter: str | None,
    search_query: str = "",
    router: Router,
    video_player: VideoPlayer,
    on_entry_focus: Callable[[LibraryEntry], None],
    is_loading: bool = False,
) -> LibraryUiState:
    if is_loading:
        return LibraryUiState(entries=[], tags=[], is_loading=True)

    tags = collect_tags(all_entries)
    filtered = [
        entry
        for entry in all_entries
        if matches_entries_filter(entry, entries_filter)
        and matches_tag_filter(entry, tag_filter)
        and matches_search_query(entry, search_query)
    ]

    ui_entries = [
        _to_list_entry(entry, router, video_player, on_entry_focus)
        for entry in filtered
    ]
    return LibraryUiState(entries=ui_entries, tags=tags, is_loading=False)


def find_entry_index_for_letter(entries: list[ListEntryUiModel], letter: str) -> int:
    if letter == "#":
        return 0
    for index, model in enumerate(entries):
        sort_name = model.name.sort_name
        if sort_name and sort_name[0].upper() == letter.upper():
            return index
    return 0


def build_alphabet_symbols(entries: list[ListEntryUiModel]) -> list[str]:
    library_letters = {
        model.name.sort_name[0].upper()
        for model in entries
        if model.name.sort_name
    }
    symbols = ["#"]
    symbols.extend(chr(code) for code in range(ord("A"), ord("Z") + 1) if chr(code) in library_letters)
    return symbols


def active_letter_for_row(entries: list[ListEntryUiModel], row: int) -> str | None:
    if row < 0 or row >= len(entries):
        return None
    sort_name = entries[row].name.sort_name
    if not sort_name:
        return None
    first = sort_name[0].upper()
    if first.isalpha():
        return first
    return "#"


def _to_list_entry(
    entry: LibraryEntry,
    router: Router,
    video_player: VideoPlayer,
    on_entry_focus: Callable[[LibraryEntry], None],
) -> ListEntryUiModel:
    def on_click() -> None:
        on_library_entry_clicked(entry, router, video_player)

    def on_focus() -> None:
        on_entry_focus(entry)

    return ListEntryUiModel(
        name=entry.name,
        entry_type=library_entry_type(entry),
        poster_path=entry.root_relative_poster_path,
        on_click=on_click,
        on_focus=on_focus,
    )
