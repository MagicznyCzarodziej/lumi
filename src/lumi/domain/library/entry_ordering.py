"""Sort keys and ordering normalization for nested library entries."""

from __future__ import annotations

from lumi.domain.library.building.file_name_parser import (
    extract_leading_episode_number,
    resolve_season_ordinal_number,
)
from lumi.domain.library.models import (
    Episode,
    EpisodesGroup,
    FilmSeries,
    FilmSeriesFilm,
    LibraryEntry,
    MediaGrouping,
    MediaGroupingEntry,
    MediaGroupingFilm,
    Series,
)


def episodes_group_sort_key(group: EpisodesGroup) -> tuple[int, str]:
    ordinal = resolve_season_ordinal_number(group.name.name, fallback_number=group.ordinal_number)
    return (ordinal, group.name.name.casefold())


def episode_sort_key(episode: Episode) -> tuple[int, str]:
    if episode.ordinal_number >= 0:
        ordinal = episode.ordinal_number
    else:
        ordinal = extract_leading_episode_number(episode.name.name) or episode.ordinal_number
    return (ordinal, episode.name.name.casefold())


def film_series_film_sort_key(film: FilmSeriesFilm) -> tuple[int, str]:
    return (film.ordinal_number, film.name.name.casefold())


def normalize_library_entry(entry: LibraryEntry) -> LibraryEntry:
    if isinstance(entry, Series):
        return _normalize_series(entry)
    if isinstance(entry, FilmSeries):
        return _normalize_film_series(entry)
    if isinstance(entry, MediaGrouping):
        return _normalize_media_grouping(entry)
    return entry


def normalize_library(entries: list[LibraryEntry]) -> list[LibraryEntry]:
    return [normalize_library_entry(entry) for entry in entries]


def _normalize_series(series: Series) -> Series:
    seasons = [_normalize_episodes_group(season) for season in series.seasons]
    seasons.sort(key=episodes_group_sort_key)
    return Series(
        id=series.id,
        name=series.name,
        root_relative_path=series.root_relative_path,
        root_relative_poster_path=series.root_relative_poster_path,
        tags=series.tags,
        franchise=series.franchise,
        seasons=seasons,
    )


def _normalize_film_series(film_series: FilmSeries) -> FilmSeries:
    films = [_normalize_film_series_film(film) for film in film_series.films]
    films.sort(key=film_series_film_sort_key)
    return FilmSeries(
        id=film_series.id,
        name=film_series.name,
        root_relative_path=film_series.root_relative_path,
        root_relative_poster_path=film_series.root_relative_poster_path,
        tags=film_series.tags,
        franchise=film_series.franchise,
        films=films,
    )


def _normalize_media_grouping(grouping: MediaGrouping) -> MediaGrouping:
    entries: list[MediaGroupingEntry] = []
    for child in grouping.entries:
        if isinstance(child, EpisodesGroup):
            entries.append(_normalize_episodes_group(child))
        elif isinstance(child, MediaGroupingFilm):
            entries.append(child)
    entries.sort(key=_media_grouping_entry_sort_key)
    return MediaGrouping(
        id=grouping.id,
        name=grouping.name,
        root_relative_path=grouping.root_relative_path,
        root_relative_poster_path=grouping.root_relative_poster_path,
        tags=grouping.tags,
        franchise=grouping.franchise,
        entries=entries,
    )


def _normalize_episodes_group(group: EpisodesGroup) -> EpisodesGroup:
    episodes = sorted(group.episodes, key=episode_sort_key)
    ordinal = resolve_season_ordinal_number(
        group.name.name,
        fallback_number=group.ordinal_number,
    )
    return EpisodesGroup(
        id=group.id,
        name=group.name,
        root_relative_path=group.root_relative_path,
        root_relative_poster_path=group.root_relative_poster_path,
        ordinal_number=ordinal,
        episodes=episodes,
    )


def _normalize_film_series_film(film: FilmSeriesFilm) -> FilmSeriesFilm:
    return film


def _media_grouping_entry_sort_key(entry: MediaGroupingEntry) -> tuple[int, int, str]:
    if isinstance(entry, EpisodesGroup):
        key = episodes_group_sort_key(entry)
        return (0, key[0], key[1])
    return (1, entry.ordinal_number, entry.name.name.casefold())
