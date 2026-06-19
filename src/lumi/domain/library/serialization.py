"""JSON serialization for library cache files."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any

from lumi.domain.library.models import (
    EntryId,
    Episode,
    EpisodesGroup,
    FilmSeries,
    FilmSeriesFilm,
    Franchise,
    Library,
    LibraryEntry,
    MediaGrouping,
    MediaGroupingEntry,
    MediaGroupingFilm,
    Name,
    Series,
    StandaloneFilm,
    VideoFile,
)

_STANDALONE_FILM = "pl.przemyslawpitus.luminark.domain.library.StandaloneFilm"
_FILM_SERIES = "pl.przemyslawpitus.luminark.domain.library.FilmSeries"
_SERIES = "pl.przemyslawpitus.luminark.domain.library.Series"
_MEDIA_GROUPING = "pl.przemyslawpitus.luminark.domain.library.MediaGrouping"
_MEDIA_GROUPING_FILM = "pl.przemyslawpitus.luminark.domain.library.MediaGroupingFilm"
_EPISODES_GROUP = "pl.przemyslawpitus.luminark.domain.library.EpisodesGroup"

_LIBRARY_ENTRY_TYPES: dict[str, type[LibraryEntry]] = {
    _STANDALONE_FILM: StandaloneFilm,
    _FILM_SERIES: FilmSeries,
    _SERIES: Series,
    _MEDIA_GROUPING: MediaGrouping,
}

_MEDIA_GROUPING_ENTRY_TYPES: dict[str, type[MediaGroupingEntry]] = {
    _MEDIA_GROUPING_FILM: MediaGroupingFilm,
    _EPISODES_GROUP: EpisodesGroup,
}


def _path(value: str) -> PurePosixPath:
    return PurePosixPath(value)


def _decode_name(data: dict[str, Any]) -> Name:
    return Name(
        name=data["name"],
        alternative_name=data.get("alternativeName"),
    )


def _encode_name(name: Name) -> dict[str, Any]:
    result: dict[str, Any] = {"name": name.name}
    if name.alternative_name is not None:
        result["alternativeName"] = name.alternative_name
    return result


def _decode_entry_id(data: dict[str, Any]) -> EntryId:
    return EntryId(id=data["id"])


def _encode_entry_id(entry_id: EntryId) -> dict[str, Any]:
    return {"id": entry_id.id}


def _decode_franchise(data: dict[str, Any] | None) -> Franchise | None:
    if data is None:
        return None
    return Franchise(name=data["name"])


def _encode_franchise(franchise: Franchise | None) -> dict[str, Any] | None:
    if franchise is None:
        return None
    return {"name": franchise.name}


def _decode_video_file(data: dict[str, Any]) -> VideoFile:
    return VideoFile(name=_decode_name(data["name"]), absolute_path=_path(data["absolutePath"]))


def _encode_video_file(video_file: VideoFile) -> dict[str, Any]:
    return {
        "name": _encode_name(video_file.name),
        "absolutePath": video_file.absolute_path.as_posix(),
    }


def _decode_episode(data: dict[str, Any]) -> Episode:
    return Episode(
        id=_decode_entry_id(data["id"]),
        name=_decode_name(data["name"]),
        root_relative_path=_path(data["rootRelativePath"]),
        ordinal_number=data["ordinalNumber"],
    )


def _encode_episode(episode: Episode) -> dict[str, Any]:
    return {
        "id": _encode_entry_id(episode.id),
        "name": _encode_name(episode.name),
        "rootRelativePath": episode.root_relative_path.as_posix(),
        "ordinalNumber": episode.ordinal_number,
    }


def _decode_episodes_group(data: dict[str, Any]) -> EpisodesGroup:
    return EpisodesGroup(
        id=_decode_entry_id(data["id"]),
        name=_decode_name(data["name"]),
        root_relative_path=_path(data["rootRelativePath"]),
        root_relative_poster_path=_path(data["rootRelativePosterPath"]),
        ordinal_number=data["ordinalNumber"],
        episodes=[_decode_episode(ep) for ep in data["episodes"]],
    )


def _encode_episodes_group(group: EpisodesGroup, *, include_type: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": _encode_entry_id(group.id),
        "name": _encode_name(group.name),
        "rootRelativePath": group.root_relative_path.as_posix(),
        "rootRelativePosterPath": group.root_relative_poster_path.as_posix(),
        "ordinalNumber": group.ordinal_number,
        "episodes": [_encode_episode(ep) for ep in group.episodes],
    }
    if include_type:
        result["type"] = _EPISODES_GROUP
    return result


def _decode_film_series_film(data: dict[str, Any]) -> FilmSeriesFilm:
    return FilmSeriesFilm(
        id=_decode_entry_id(data["id"]),
        name=_decode_name(data["name"]),
        root_relative_path=_path(data["rootRelativePath"]),
        root_relative_poster_path=_path(data["rootRelativePosterPath"]),
        ordinal_number=data["ordinalNumber"],
        video_files=[_decode_video_file(vf) for vf in data["videoFiles"]],
    )


def _encode_film_series_film(film: FilmSeriesFilm) -> dict[str, Any]:
    return {
        "id": _encode_entry_id(film.id),
        "name": _encode_name(film.name),
        "rootRelativePath": film.root_relative_path.as_posix(),
        "rootRelativePosterPath": film.root_relative_poster_path.as_posix(),
        "ordinalNumber": film.ordinal_number,
        "videoFiles": [_encode_video_file(vf) for vf in film.video_files],
    }


def _decode_media_grouping_film(data: dict[str, Any]) -> MediaGroupingFilm:
    return MediaGroupingFilm(
        id=_decode_entry_id(data["id"]),
        name=_decode_name(data["name"]),
        root_relative_path=_path(data["rootRelativePath"]),
        root_relative_poster_path=_path(data["rootRelativePosterPath"]),
        ordinal_number=data["ordinalNumber"],
        video_files=[_decode_video_file(vf) for vf in data["videoFiles"]],
    )


def _encode_media_grouping_film(film: MediaGroupingFilm) -> dict[str, Any]:
    return {
        "type": _MEDIA_GROUPING_FILM,
        "id": _encode_entry_id(film.id),
        "name": _encode_name(film.name),
        "rootRelativePath": film.root_relative_path.as_posix(),
        "rootRelativePosterPath": film.root_relative_poster_path.as_posix(),
        "ordinalNumber": film.ordinal_number,
        "videoFiles": [_encode_video_file(vf) for vf in film.video_files],
    }


def _decode_media_grouping_entry(data: dict[str, Any]) -> MediaGroupingEntry:
    entry_type = data["type"]
    if entry_type == _MEDIA_GROUPING_FILM:
        return _decode_media_grouping_film(data)
    if entry_type == _EPISODES_GROUP:
        return _decode_episodes_group(data)
    raise ValueError(f"Unknown media grouping entry type: {entry_type}")


def _encode_media_grouping_entry(entry: MediaGroupingEntry) -> dict[str, Any]:
    if isinstance(entry, MediaGroupingFilm):
        return _encode_media_grouping_film(entry)
    return _encode_episodes_group(entry, include_type=True)


def _decode_library_entry(data: dict[str, Any]) -> LibraryEntry:
    entry_type = data["type"]
    cls = _LIBRARY_ENTRY_TYPES.get(entry_type)
    if cls is None:
        raise ValueError(f"Unknown library entry type: {entry_type}")

    id_ = _decode_entry_id(data["id"])
    name = _decode_name(data["name"])
    root_relative_path = _path(data["rootRelativePath"])
    root_relative_poster_path = _path(data["rootRelativePosterPath"])
    tags = frozenset(data.get("tags", []))
    franchise = _decode_franchise(data.get("franchise"))

    if cls is StandaloneFilm:
        return StandaloneFilm(
            id=id_,
            name=name,
            root_relative_path=root_relative_path,
            root_relative_poster_path=root_relative_poster_path,
            tags=tags,
            franchise=franchise,
            video_files=[_decode_video_file(vf) for vf in data["videoFiles"]],
        )
    if cls is FilmSeries:
        return FilmSeries(
            id=id_,
            name=name,
            root_relative_path=root_relative_path,
            root_relative_poster_path=root_relative_poster_path,
            tags=tags,
            franchise=franchise,
            films=[_decode_film_series_film(f) for f in data["films"]],
        )
    if cls is Series:
        return Series(
            id=id_,
            name=name,
            root_relative_path=root_relative_path,
            root_relative_poster_path=root_relative_poster_path,
            tags=tags,
            franchise=franchise,
            seasons=[_decode_episodes_group(s) for s in data["seasons"]],
        )
    if cls is MediaGrouping:
        return MediaGrouping(
            id=id_,
            name=name,
            root_relative_path=root_relative_path,
            root_relative_poster_path=root_relative_poster_path,
            tags=tags,
            franchise=franchise,
            entries=[_decode_media_grouping_entry(e) for e in data["entries"]],
        )
    raise ValueError(f"Unhandled library entry type: {entry_type}")


def _encode_library_entry(entry: LibraryEntry) -> dict[str, Any]:
    if isinstance(entry, StandaloneFilm):
        type_name = _STANDALONE_FILM
        extra = {"videoFiles": [_encode_video_file(vf) for vf in entry.video_files]}
    elif isinstance(entry, FilmSeries):
        type_name = _FILM_SERIES
        extra = {"films": [_encode_film_series_film(f) for f in entry.films]}
    elif isinstance(entry, Series):
        type_name = _SERIES
        extra = {
            "seasons": [_encode_episodes_group(s, include_type=False) for s in entry.seasons],
        }
    elif isinstance(entry, MediaGrouping):
        type_name = _MEDIA_GROUPING
        extra = {"entries": [_encode_media_grouping_entry(e) for e in entry.entries]}
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


def library_from_json(text: str) -> Library:
    data = json.loads(text)
    return Library(entries=[_decode_library_entry(entry) for entry in data["entries"]])


def library_to_json(library: Library, *, pretty: bool = False) -> str:
    payload = {"entries": [_encode_library_entry(entry) for entry in library.entries]}
    if pretty:
        return json.dumps(payload, indent=4)
    return json.dumps(payload, separators=(",", ":"))
