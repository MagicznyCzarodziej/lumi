"""Background subtitle file discovery worker."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from lumi.domain.filesystem.files_lister import FilesLister
from lumi.domain.playback import PlaybackUriResolver
from lumi.domain.subtitles.discovery import discover_subtitle_files


class SubtitleDiscoveryWorker(QRunnable):
    """Lists subtitle files in the video directory off the UI thread."""

    def __init__(
        self,
        files_lister: FilesLister,
        video_path: PurePosixPath,
        subtitle_extensions: set[str],
        *,
        library_root: PurePosixPath | None = None,
        video_extensions: set[str] | None = None,
        playback_uri_resolver: PlaybackUriResolver | None = None,
    ) -> None:
        super().__init__()
        self.video_path = video_path
        self._files_lister = files_lister
        self._subtitle_extensions = subtitle_extensions
        self._library_root = library_root
        self._video_extensions = video_extensions
        self._playback_uri_resolver = playback_uri_resolver
        self.signals = _SubtitleDiscoverySignals()

    @Slot()
    def run(self) -> None:
        try:
            hint_path = self.video_path
            if self._playback_uri_resolver is not None:
                try:
                    hint_path = self._playback_uri_resolver.resolve_path(self.video_path)
                except OSError:
                    hint_path = self.video_path
            paths = discover_subtitle_files(
                self._files_lister,
                hint_path,
                self._subtitle_extensions,
                library_root=self._library_root,
                video_extensions=self._video_extensions,
            )
            self.signals.finished.emit(self.video_path, paths)
        except Exception as exc:
            self.signals.failed.emit(self.video_path, str(exc))


class _SubtitleDiscoverySignals(QObject):
    finished = Signal(object, object)
    failed = Signal(object, str)
