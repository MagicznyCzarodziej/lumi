"""Library entry lookup helpers for navigation and controllers."""

from __future__ import annotations

from lumi.domain.library.models import (
    EpisodesGroup,
    FilmSeries,
    LibraryEntry,
    MediaGrouping,
    MediaGroupingEntry,
    Series,
)


def find_top_level_entry(entries: list[LibraryEntry], entry_id: str) -> LibraryEntry | None:
    return next((entry for entry in entries if entry.id.id == entry_id), None)


def find_series(entries: list[LibraryEntry], series_id: str) -> Series | None:
    entry = find_top_level_entry(entries, series_id)
    return entry if isinstance(entry, Series) else None


def find_film_series(entries: list[LibraryEntry], film_series_id: str) -> FilmSeries | None:
    entry = find_top_level_entry(entries, film_series_id)
    return entry if isinstance(entry, FilmSeries) else None


def find_media_grouping(entries: list[LibraryEntry], media_grouping_id: str) -> MediaGrouping | None:
    entry = find_top_level_entry(entries, media_grouping_id)
    return entry if isinstance(entry, MediaGrouping) else None


def find_episodes_group(entries: list[LibraryEntry], episodes_group_id: str) -> tuple[Series | None, EpisodesGroup | None]:
    for entry in entries:
        if isinstance(entry, Series):
            for season in entry.seasons:
                if season.id.id == episodes_group_id:
                    return entry, season
        if isinstance(entry, MediaGrouping):
            for child in entry.entries:
                if isinstance(child, EpisodesGroup) and child.id.id == episodes_group_id:
                    return None, child
    return None, None


def find_media_grouping_episodes_group(
    entries: list[LibraryEntry],
    media_grouping_id: str,
    episodes_group_id: str,
) -> tuple[MediaGrouping | None, EpisodesGroup | None]:
    grouping = find_media_grouping(entries, media_grouping_id)
    if grouping is None:
        return None, None
    for child in grouping.entries:
        if isinstance(child, EpisodesGroup) and child.id.id == episodes_group_id:
            return grouping, child
    return grouping, None
