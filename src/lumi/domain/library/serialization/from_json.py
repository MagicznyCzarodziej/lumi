from __future__ import annotations

import json
from typing import Any

from lumi.domain.library.models import Library, Name, EntryId, Franchise, VideoFile, Episode, EpisodesGroup, \
    FilmSeriesFilm, MediaGroupingFilm, MediaGroupingEntry, LibraryEntry, StandaloneFilm, FilmSeries, Series, \
    MediaGrouping
from lumi.domain.library.serialization.path import _path
from lumi.domain.library.serialization.types import _MEDIA_GROUPING_FILM, _EPISODES_GROUP, _LIBRARY_ENTRY_TYPES


def library_from_json(text: str) -> Library:
    data = json.loads(text)
    return Library(
        entries=[_decode_library_entry(entry) for entry in data["entries"]]
    )


def _decode_library_entry(data: dict[str, Any]) -> LibraryEntry:
    raw_type = data["type"]
    entry_type = _LIBRARY_ENTRY_TYPES.get(raw_type)
    if entry_type is None:
        raise ValueError(f"Unknown library entry type: {raw_type}")

    id_ = _decode_entry_id(data["id"])
    name = _decode_name(data["name"])
    root_relative_path = _path(data["rootRelativePath"])
    root_relative_poster_path = _path(data["rootRelativePosterPath"])
    tags = frozenset(data.get("tags", []))
    franchise = _decode_franchise(data.get("franchise"))

    if entry_type is StandaloneFilm:
        return StandaloneFilm(
            id=id_,
            name=name,
            root_relative_path=root_relative_path,
            root_relative_poster_path=root_relative_poster_path,
            tags=tags,
            franchise=franchise,
            video_files=[_decode_video_file(video_file) for video_file in data["videoFiles"]],
        )
    if entry_type is FilmSeries:
        return FilmSeries(
            id=id_,
            name=name,
            root_relative_path=root_relative_path,
            root_relative_poster_path=root_relative_poster_path,
            tags=tags,
            franchise=franchise,
            films=[_decode_film_series_film(film) for film in data["films"]],
        )
    if entry_type is Series:
        return Series(
            id=id_,
            name=name,
            root_relative_path=root_relative_path,
            root_relative_poster_path=root_relative_poster_path,
            tags=tags,
            franchise=franchise,
            seasons=[_decode_episodes_group(season) for season in data["seasons"]],
        )
    if entry_type is MediaGrouping:
        return MediaGrouping(
            id=id_,
            name=name,
            root_relative_path=root_relative_path,
            root_relative_poster_path=root_relative_poster_path,
            tags=tags,
            franchise=franchise,
            entries=[_decode_media_grouping_entry(entry) for entry in data["entries"]],
        )
    raise ValueError(f"Unhandled library entry type: {raw_type}")


def _decode_name(data: dict[str, Any]) -> Name:
    return Name(
        name=data["name"],
        alternative_name=data.get("alternativeName"),
    )


def _decode_entry_id(data: dict[str, Any]) -> EntryId:
    return EntryId(id=data["id"])


def _decode_franchise(data: dict[str, Any] | None) -> Franchise | None:
    if data is None:
        return None
    return Franchise(name=data["name"])


def _decode_video_file(data: dict[str, Any]) -> VideoFile:
    return VideoFile(
        name=_decode_name(data["name"]),
        absolute_path=_path(data["absolutePath"])
    )


def _decode_episode(data: dict[str, Any]) -> Episode:
    return Episode(
        id=_decode_entry_id(data["id"]),
        name=_decode_name(data["name"]),
        root_relative_path=_path(data["rootRelativePath"]),
        ordinal_number=data["ordinalNumber"],
    )


def _decode_episodes_group(data: dict[str, Any]) -> EpisodesGroup:
    return EpisodesGroup(
        id=_decode_entry_id(data["id"]),
        name=_decode_name(data["name"]),
        root_relative_path=_path(data["rootRelativePath"]),
        root_relative_poster_path=_path(data["rootRelativePosterPath"]),
        ordinal_number=data["ordinalNumber"],
        episodes=[_decode_episode(episode) for episode in data["episodes"]],
    )


def _decode_film_series_film(data: dict[str, Any]) -> FilmSeriesFilm:
    return FilmSeriesFilm(
        id=_decode_entry_id(data["id"]),
        name=_decode_name(data["name"]),
        root_relative_path=_path(data["rootRelativePath"]),
        root_relative_poster_path=_path(data["rootRelativePosterPath"]),
        ordinal_number=data["ordinalNumber"],
        video_files=[_decode_video_file(video_file) for video_file in data["videoFiles"]],
    )


def _decode_media_grouping_film(data: dict[str, Any]) -> MediaGroupingFilm:
    return MediaGroupingFilm(
        id=_decode_entry_id(data["id"]),
        name=_decode_name(data["name"]),
        root_relative_path=_path(data["rootRelativePath"]),
        root_relative_poster_path=_path(data["rootRelativePosterPath"]),
        ordinal_number=data["ordinalNumber"],
        video_files=[_decode_video_file(video_file) for video_file in data["videoFiles"]],
    )


def _decode_media_grouping_entry(data: dict[str, Any]) -> MediaGroupingEntry:
    entry_type = data["type"]
    if entry_type == _MEDIA_GROUPING_FILM:
        return _decode_media_grouping_film(data)
    if entry_type == _EPISODES_GROUP:
        return _decode_episodes_group(data)
    raise ValueError(f"Unknown media grouping entry type: {entry_type}")
