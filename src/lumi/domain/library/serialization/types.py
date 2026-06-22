from __future__ import annotations

from lumi.domain.library.models import (
    LibraryEntry,
    StandaloneFilm,
    FilmSeries,
    Series,
    MediaGrouping,
    MediaGroupingEntry,
    MediaGroupingFilm,
    EpisodesGroup
)

_STANDALONE_FILM = "STANDALONE_FILM"
_FILM_SERIES = "FILM_SERIES"
_SERIES = "SERIES"
_MEDIA_GROUPING = "MEDIA_GROUPING"
_MEDIA_GROUPING_FILM = "MEDIA_GROUPING_FILM"
_EPISODES_GROUP = "EPISODES_GROUP"

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
