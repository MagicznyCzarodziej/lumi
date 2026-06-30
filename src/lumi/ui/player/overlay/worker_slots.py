"""Qt slots for background worker callbacks — must live on a QObject in the UI thread."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot

from lumi.domain.subtitles.browse import BrowseRow

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay


class OverlayWorkerSlots(QObject):
    def __init__(self, overlay: PlayerOverlay) -> None:
        super().__init__(overlay)
        self._overlay = overlay

    @Slot(object, object, object)
    def browse_loaded(
        self,
        requested: PurePosixPath,
        resolved: PurePosixPath,
        rows: list[BrowseRow],
    ) -> None:
        self._overlay.browse.on_browse_loaded(requested, resolved, rows)

    @Slot(object, str)
    def browse_failed(self, directory: PurePosixPath, message: str) -> None:
        self._overlay.browse.on_browse_failed(directory, message)

    @Slot(object, object, bool)
    def napi_download_finished(
        self,
        video_path: PurePosixPath,
        local_path: Path,
        from_cache: bool,
    ) -> None:
        self._overlay.napi.on_download_finished(video_path, local_path, from_cache)

    @Slot(object, str)
    def napi_download_failed(self, video_path: PurePosixPath, message: str) -> None:
        self._overlay.napi.on_download_failed(video_path, message)

    @Slot(object, object)
    def napi_save_finished(self, video_path: PurePosixPath, sidecar: PurePosixPath) -> None:
        self._overlay.napi.on_save_finished(video_path, sidecar)

    @Slot(object, object)
    def napi_save_exists(self, video_path: PurePosixPath, sidecar: PurePosixPath) -> None:
        self._overlay.napi.on_save_exists(video_path, sidecar)

    @Slot(object, str)
    def napi_save_failed(self, video_path: PurePosixPath, message: str) -> None:
        self._overlay.napi.on_save_failed(video_path, message)
