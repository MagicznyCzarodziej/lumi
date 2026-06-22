from __future__ import annotations

import json
from typing import Any

from lumi.domain.library.models import Library, Name, EntryId, Franchise, VideoFile, Episode, EpisodesGroup, \
    FilmSeriesFilm, MediaGroupingFilm, MediaGroupingEntry, LibraryEntry, StandaloneFilm, FilmSeries, Series, \
    MediaGrouping
from lumi.domain.library.serialization.types import _EPISODES_GROUP, _MEDIA_GROUPING_FILM, _STANDALONE_FILM, \
    _FILM_SERIES, _SERIES, _MEDIA_GROUPING


def library_to_json(library: Library) -> str:
    payload = {
        "entries": [_encode_library_entry(entry) for entry in library.entries]
    }
    return json.dumps(payload, separators=(",", ":"))


def _encode_library_entry(entry: LibraryEntry) -> dict[str, Any]:
    if isinstance(entry, StandaloneFilm):
        type_name = _STANDALONE_FILM
        extra = {"videoFiles": [_encode_video_file(video_file) for video_file in entry.video_files]}
    elif isinstance(entry, FilmSeries):
        type_name = _FILM_SERIES
        extra = {"films": [_encode_film_series_film(film) for film in entry.films]}
    elif isinstance(entry, Series):
        type_name = _SERIES
        extra = {
            "seasons": [_encode_episodes_group(season, include_type=False) for season in entry.seasons],
        }
    elif isinstance(entry, MediaGrouping):
        type_name = _MEDIA_GROUPING
        extra = {"entries": [_encode_media_grouping_entry(entry) for entry in entry.entries]}
    else:
        raise TypeError(f"Unknown entry type: {type(entry)!r}")

    return {
        "type": type_name,
        "id": _encode_entry_id(entry.id),
        "name": _encode_name(entry.name),
        "rootRelativePath": entry.root_relative_path.as_posix(),
        "rootRelativePosterPath": entry.root_relative_poster_path.as_posix(),
        "tags": sorted(entry.tags),
        "franchise": _encode_franchise(entry.franchise),
        **extra,
    }


def _encode_name(name: Name) -> dict[str, Any]:
    result: dict[str, Any] = {"name": name.name}
    if name.alternative_name is not None:
        result["alternativeName"] = name.alternative_name
    return result


def _encode_entry_id(entry_id: EntryId) -> dict[str, Any]:
    return {"id": entry_id.id}


def _encode_franchise(franchise: Franchise | None) -> dict[str, Any] | None:
    if franchise is None:
        return None
    return {"name": franchise.name}


def _encode_video_file(video_file: VideoFile) -> dict[str, Any]:
    return {
        "name": _encode_name(video_file.name),
        "absolutePath": video_file.absolute_path.as_posix(),
    }


def _encode_episode(episode: Episode) -> dict[str, Any]:
    return {
        "id": _encode_entry_id(episode.id),
        "name": _encode_name(episode.name),
        "rootRelativePath": episode.root_relative_path.as_posix(),
        "ordinalNumber": episode.ordinal_number,
    }


def _encode_episodes_group(group: EpisodesGroup, *, include_type: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": _encode_entry_id(group.id),
        "name": _encode_name(group.name),
        "rootRelativePath": group.root_relative_path.as_posix(),
        "rootRelativePosterPath": group.root_relative_poster_path.as_posix(),
        "ordinalNumber": group.ordinal_number,
        "episodes": [_encode_episode(episode) for episode in group.episodes],
    }
    if include_type:
        result["type"] = _EPISODES_GROUP
    return result


def _encode_film_series_film(film: FilmSeriesFilm) -> dict[str, Any]:
    return {
        "id": _encode_entry_id(film.id),
        "name": _encode_name(film.name),
        "rootRelativePath": film.root_relative_path.as_posix(),
        "rootRelativePosterPath": film.root_relative_poster_path.as_posix(),
        "ordinalNumber": film.ordinal_number,
        "videoFiles": [_encode_video_file(video_file) for video_file in film.video_files],
    }


def _encode_media_grouping_film(film: MediaGroupingFilm) -> dict[str, Any]:
    return {
        "type": _MEDIA_GROUPING_FILM,
        "id": _encode_entry_id(film.id),
        "name": _encode_name(film.name),
        "rootRelativePath": film.root_relative_path.as_posix(),
        "rootRelativePosterPath": film.root_relative_poster_path.as_posix(),
        "ordinalNumber": film.ordinal_number,
        "videoFiles": [_encode_video_file(video_file) for video_file in film.video_files],
    }


def _encode_media_grouping_entry(entry: MediaGroupingEntry) -> dict[str, Any]:
    if isinstance(entry, MediaGroupingFilm):
        return _encode_media_grouping_film(entry)
    return _encode_episodes_group(entry, include_type=True)
