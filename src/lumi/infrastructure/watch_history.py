"""Local JSON implementation of the watch-history domain boundary."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from lumi.domain.recent_watch import RecentWatchRecord
from lumi.domain.watch_history import WatchHistory
from lumi.infrastructure.watch_progress import (
    forget_playback as forget_playback_record,
    load_recent_watch_records,
    load_watch_position,
    save_recent_watch_record,
    save_watch_position,
)


class JsonWatchHistory(WatchHistory):
    """Coordinates the compatible progress and recent-watch JSON stores."""

    def __init__(
        self,
        *,
        progress_path: Path | None = None,
        recent_path: Path | None = None,
    ) -> None:
        self._progress_path = progress_path
        self._recent_path = recent_path

    def resume_position(
        self,
        library_path: PurePosixPath,
        *,
        duration: float | None = None,
    ) -> float | None:
        return load_watch_position(
            library_path,
            duration=duration,
            path=self._progress_path,
        )

    def record_playback(
        self,
        library_path: PurePosixPath,
        position: float,
        *,
        duration: float | None = None,
    ) -> None:
        save_watch_position(
            library_path,
            position,
            duration=duration,
            path=self._progress_path,
        )
        save_recent_watch_record(
            library_path,
            position,
            duration=duration,
            path=self._recent_path,
        )

    def recent_entries(self) -> list[RecentWatchRecord]:
        return load_recent_watch_records(path=self._recent_path)

    def forget_playback(self, library_path: PurePosixPath) -> None:
        forget_playback_record(
            library_path,
            progress_path=self._progress_path,
            recent_path=self._recent_path,
        )
