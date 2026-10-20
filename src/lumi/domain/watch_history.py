"""Domain boundary for locally persisted playback history."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol

from lumi.domain.recent_watch import RecentWatchRecord


class WatchHistory(Protocol):
    """Stores resumable playback and exposes entries for the recent-watch view."""

    def resume_position(
        self,
        library_path: PurePosixPath,
        *,
        duration: float | None = None,
    ) -> float | None:
        """Return a valid saved resume position for a library video."""

    def record_playback(
        self,
        library_path: PurePosixPath,
        position: float,
        *,
        duration: float | None = None,
    ) -> None:
        """Persist a playback observation using the shared resume policy."""

    def recent_entries(self) -> list[RecentWatchRecord]:
        """Return local resumable watches in persistence order."""

    def forget_playback(self, library_path: PurePosixPath) -> None:
        """Drop resume data and remove the title from Recently watched."""
