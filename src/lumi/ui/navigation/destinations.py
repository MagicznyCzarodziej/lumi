"""Navigation destination types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class LibraryDestination:
    pass


@dataclass(frozen=True)
class SeriesDestination:
    series_id: str


@dataclass(frozen=True)
class EpisodesGroupDestination:
    episodes_group_id: str


@dataclass(frozen=True)
class FilmSeriesDestination:
    film_series_id: str


@dataclass(frozen=True)
class MediaGroupingDestination:
    media_grouping_id: str


@dataclass(frozen=True)
class MediaGroupingEpisodesGroupDestination:
    media_grouping_id: str
    episodes_group_id: str


Destination = Union[
    LibraryDestination,
    SeriesDestination,
    EpisodesGroupDestination,
    FilmSeriesDestination,
    MediaGroupingDestination,
    MediaGroupingEpisodesGroupDestination,
]

LIBRARY = LibraryDestination()
