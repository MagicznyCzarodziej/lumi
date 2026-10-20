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
    Name,
    Series,
    StandaloneFilm,
    VideoFile,
)

RESUME_END_THRESHOLD_SECONDS = 30.0
RESUME_END_THRESHOLD_FRACTION = 0.95
MIN_SAVE_POSITION_SECONDS = 3.0


@dataclass(frozen=True)
class RecentWatchRecord:
    """A playback record for Recently watched, keyed by its library path."""

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
    playable_name: Name
    episode: Episode | None = None
    episodes_group: EpisodesGroup | None = None


def coerce_saved_playback_position(
    position: float,
    alternate_position: float,
    duration: float | None,
) -> float:
    """Pick a timeline bookmark to persist, including near-end and completed sessions."""
    best = max(position, alternate_position)
    if duration is not None and math.isfinite(duration) and duration > 0:
        if is_playback_complete(best, duration):
            return min(
                duration,
                max(best, duration * RESUME_END_THRESHOLD_FRACTION),
            )
    if best >= MIN_SAVE_POSITION_SECONDS:
        return best
    return position


def resume_timeline_fraction(position: float, duration: float | None) -> float | None:
    """Return how far into the media timeline playback stopped (0–1), not watch-time."""
    if duration is None or not math.isfinite(duration) or duration <= 0:
        return None
    if not math.isfinite(position):
        return None
    return min(1.0, max(0.0, position / duration))


def resume_timeline_percent(position: float, duration: float | None) -> int | None:
    """Integer percent for UI labels derived from ``resume_timeline_fraction``."""
    if is_playback_complete(position, duration):
        return 100
    fraction = resume_timeline_fraction(position, duration)
    if fraction is None:
        return None
    return int(fraction * 100)


def is_playback_complete(position: float, duration: float | None) -> bool:
    """Return whether playback reached the end (for Watch again, not resume)."""
    if duration is None or not math.isfinite(duration) or duration <= 0:
        return False
    if not math.isfinite(position):
        return False
    return (
        position >= duration - RESUME_END_THRESHOLD_SECONDS
        or position >= duration * RESUME_END_THRESHOLD_FRACTION
    )


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


def is_recent_watch_record(position: float, duration: float | None) -> bool:
    """Return whether a playback session belongs on Recently watched."""
    if not math.isfinite(position) or position < MIN_SAVE_POSITION_SECONDS:
        return False
    if is_playback_complete(position, duration):
        return True
    return is_resumable_position(position, duration)


def resolve_recent_watch_records(
    records: Iterable[RecentWatchRecord],
    library: Library,
) -> list[ResolvedRecentWatch]:
    """Resolve valid persisted records against media still in the library."""
    resolved: list[ResolvedRecentWatch] = []
    for record in records:
        if not is_recent_watch_record(record.position, record.duration):
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
        if isinstance(entry, StandaloneFilm) and video_files_refer_to_path(
            entry.video_files, record.library_path
        ):
            return _resolved_record(record, entry, playable_name=entry.name)
        if isinstance(entry, FilmSeries):
            for film in entry.films:
                if video_files_refer_to_path(film.video_files, record.library_path):
                    return _resolved_record(record, entry, playable_name=film.name)
        if isinstance(entry, Series):
            for season in entry.seasons:
                if match := _matching_episode(season, record.library_path):
                    return _resolved_record(
                        record,
                        entry,
                        playable_name=match.name,
                        episode=match,
                        episodes_group=season,
                    )
        if isinstance(entry, MediaGrouping):
            for child in entry.entries:
                if isinstance(child, MediaGroupingFilm) and video_files_refer_to_path(
                    child.video_files, record.library_path
                ):
                    return _resolved_record(record, entry, playable_name=child.name)
                if isinstance(child, EpisodesGroup) and (
                    match := _matching_episode(child, record.library_path)
                ):
                    return _resolved_record(
                        record,
                        entry,
                        playable_name=match.name,
                        episode=match,
                        episodes_group=child,
                    )
    return None


def _resolved_record(
    record: RecentWatchRecord,
    entry: LibraryEntry,
    *,
    playable_name: Name,
    episode: Episode | None = None,
    episodes_group: EpisodesGroup | None = None,
) -> ResolvedRecentWatch:
    return ResolvedRecentWatch(
        entry=entry,
        library_path=record.library_path,
        position=record.position,
        duration=record.duration,
        watched_at=record.watched_at,
        playable_name=playable_name,
        episode=episode,
        episodes_group=episodes_group,
    )


def video_files_refer_to_path(video_files: Iterable[VideoFile], path: PurePosixPath) -> bool:
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
