"""Domain values shared by recently watched persistence and presentation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Iterable

from lumi.domain.library.episode_navigation import paths_refer_to_same_file
from lumi.domain.library.models import (
    Episode,
    EpisodesGroup,
    FilmSeries,
    Library,
    LibraryEntry,
    MediaGrouping,
    MediaGroupingFilm,
    Series,
    StandaloneFilm,
    VideoFile,
)

RESUME_END_THRESHOLD_SECONDS = 30.0
RESUME_END_THRESHOLD_FRACTION = 0.95
MIN_SAVE_POSITION_SECONDS = 3.0


@dataclass(frozen=True)
class RecentWatchRecord:
    """A resumable playback record, keyed by its library path."""

    library_path: PurePosixPath
    position: float
    duration: float | None
    watched_at: datetime

    def __post_init__(self) -> None:
        if not math.isfinite(self.position):
            raise ValueError("position must be finite")
        if self.duration is not None and (
            not math.isfinite(self.duration) or self.duration <= 0
        ):
            raise ValueError("duration must be finite and positive when present")
        if self.watched_at.tzinfo is None or self.watched_at.utcoffset() is None:
            raise ValueError("watched_at must be timezone-aware")
        object.__setattr__(self, "watched_at", self.watched_at.astimezone(UTC))


@dataclass(frozen=True)
class ResolvedRecentWatch:
    """A recent watch record matched to media in the current library."""

    entry: LibraryEntry
    library_path: PurePosixPath
    position: float
    duration: float | None
    watched_at: datetime
    episode: Episode | None = None


def is_resumable_position(position: float, duration: float | None) -> bool:
    """Return whether playback is far enough from both ends to resume."""
    if not math.isfinite(position) or position < MIN_SAVE_POSITION_SECONDS:
        return False
    if duration is None:
        return True
    if not math.isfinite(duration) or duration <= 0:
        return False
    return (
        position < duration - RESUME_END_THRESHOLD_SECONDS
        and position < duration * RESUME_END_THRESHOLD_FRACTION
    )


def resolve_recent_watch_records(
    records: Iterable[RecentWatchRecord],
    library: Library,
) -> list[ResolvedRecentWatch]:
    """Resolve valid persisted records against media still in the library."""
    resolved: list[ResolvedRecentWatch] = []
    for record in records:
        if not is_resumable_position(record.position, record.duration):
            continue
        match = _resolve_record(record, library.entries)
        if match is not None:
            resolved.append(match)
    return sorted(resolved, key=lambda item: item.watched_at, reverse=True)


def _resolve_record(
    record: RecentWatchRecord,
    entries: Iterable[LibraryEntry],
) -> ResolvedRecentWatch | None:
    for entry in entries:
        if isinstance(entry, StandaloneFilm) and _matches_video_files(
            entry.video_files, record.library_path
        ):
            return _resolved_record(record, entry)
        if isinstance(entry, FilmSeries):
            for film in entry.films:
                if _matches_video_files(film.video_files, record.library_path):
                    return _resolved_record(record, entry)
        if isinstance(entry, Series):
            for season in entry.seasons:
                if match := _matching_episode(season, record.library_path):
                    return _resolved_record(record, entry, episode=match)
        if isinstance(entry, MediaGrouping):
            for child in entry.entries:
                if isinstance(child, MediaGroupingFilm) and _matches_video_files(
                    child.video_files, record.library_path
                ):
                    return _resolved_record(record, entry)
                if isinstance(child, EpisodesGroup) and (
                    match := _matching_episode(child, record.library_path)
                ):
                    return _resolved_record(record, entry, episode=match)
    return None


def _resolved_record(
    record: RecentWatchRecord,
    entry: LibraryEntry,
    *,
    episode: Episode | None = None,
) -> ResolvedRecentWatch:
    return ResolvedRecentWatch(
        entry=entry,
        library_path=record.library_path,
        position=record.position,
        duration=record.duration,
        watched_at=record.watched_at,
        episode=episode,
    )


def _matches_video_files(video_files: Iterable[VideoFile], path: PurePosixPath) -> bool:
    return any(paths_refer_to_same_file(video_file.absolute_path, path) for video_file in video_files)


def _matching_episode(group: EpisodesGroup, path: PurePosixPath) -> Episode | None:
    return next(
        (
            episode
            for episode in group.episodes
            if paths_refer_to_same_file(episode.root_relative_path, path)
        ),
        None,
    )
