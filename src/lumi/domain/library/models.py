"""Library domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Union

_ARTICLES = ("a ", "an ", "the ")


def compute_sort_name(name: str) -> str:
    for article in _ARTICLES:
        if name.lower().startswith(article):
            return name[len(article) :] + ", " + name[: len(article) - 1]
    return name


@dataclass(frozen=True)
class EntryId:
    id: str


@dataclass(frozen=True)
class Name:
    name: str
    alternative_name: str | None = None
    sort_name: str = field(default="")

    def __post_init__(self) -> None:
        if not self.sort_name:
            object.__setattr__(self, "sort_name", compute_sort_name(self.name))


@dataclass(frozen=True)
class Franchise:
    name: str


@dataclass(frozen=True)
class VideoFile:
    name: Name
    absolute_path: PurePosixPath


@dataclass(frozen=True)
class Episode:
    id: EntryId
    name: Name
    root_relative_path: PurePosixPath
    ordinal_number: int


@dataclass(frozen=True)
class EpisodesGroup:
    id: EntryId
    name: Name
    root_relative_path: PurePosixPath
    root_relative_poster_path: PurePosixPath
    ordinal_number: int
    episodes: list[Episode]


@dataclass(frozen=True)
class FilmSeriesFilm:
    id: EntryId
    name: Name
    root_relative_path: PurePosixPath
    root_relative_poster_path: PurePosixPath
    ordinal_number: int
    video_files: list[VideoFile]


@dataclass(frozen=True)
class MediaGroupingFilm:
    id: EntryId
    name: Name
    root_relative_path: PurePosixPath
    root_relative_poster_path: PurePosixPath
    ordinal_number: int
    video_files: list[VideoFile]


@dataclass(frozen=True)
class StandaloneFilm:
    id: EntryId
    name: Name
    root_relative_path: PurePosixPath
    root_relative_poster_path: PurePosixPath
    tags: frozenset[str]
    franchise: Franchise | None
    video_files: list[VideoFile]


@dataclass(frozen=True)
class FilmSeries:
    id: EntryId
    name: Name
    root_relative_path: PurePosixPath
    root_relative_poster_path: PurePosixPath
    tags: frozenset[str]
    franchise: Franchise | None
    films: list[FilmSeriesFilm]


@dataclass(frozen=True)
class Series:
    id: EntryId
    name: Name
    root_relative_path: PurePosixPath
    root_relative_poster_path: PurePosixPath
    tags: frozenset[str]
    franchise: Franchise | None
    seasons: list[EpisodesGroup]


@dataclass(frozen=True)
class MediaGrouping:
    id: EntryId
    name: Name
    root_relative_path: PurePosixPath
    root_relative_poster_path: PurePosixPath
    tags: frozenset[str]
    franchise: Franchise | None
    entries: list[MediaGroupingEntry]


MediaGroupingEntry = Union[MediaGroupingFilm, EpisodesGroup]
LibraryEntry = Union[StandaloneFilm, FilmSeries, Series, MediaGrouping]


@dataclass(frozen=True)
class Library:
    entries: list[LibraryEntry]
