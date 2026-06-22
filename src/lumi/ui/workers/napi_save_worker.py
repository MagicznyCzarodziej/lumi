"""Background save of cached NapiProjekt subtitles to the library share."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from lumi.domain.filesystem.file_writer import FileWriter
from lumi.domain.playback import PlaybackUriResolver
from lumi.domain.subtitles.cache import SubtitleCache
from lumi.domain.subtitles.saved_state import NapiSavedStateStore
from lumi.domain.subtitles.sidecar_path import subtitle_sidecar_path


class NapiSaveWorker(QRunnable):
    """Writes a cached subtitle beside the video on SMB and marks it saved."""

    def __init__(
        self,
        video_path: PurePosixPath,
        *,
        subtitle_cache: SubtitleCache,
        file_writer: FileWriter,
        saved_state: NapiSavedStateStore,
        overwrite: bool = False,
        playback_uri_resolver: PlaybackUriResolver | None = None,
    ) -> None:
        super().__init__()
        self.video_path = video_path
        self._subtitle_cache = subtitle_cache
        self._file_writer = file_writer
        self._saved_state = saved_state
        self._overwrite = overwrite
        self._playback_uri_resolver = playback_uri_resolver
        self.signals = _NapiSaveSignals()

    def _resolved_video_path(self) -> PurePosixPath:
        if self._playback_uri_resolver is None:
            return self.video_path
        try:
            return self._playback_uri_resolver.resolve_path(self.video_path)
        except OSError:
            return self.video_path

    @Slot()
    def run(self) -> None:
        path = self.video_path
        try:
            data = self._subtitle_cache.read(path)
            if data is None:
                self.signals.failed.emit(path, "No cached subtitle to save")
                return

            sidecar = subtitle_sidecar_path(self._resolved_video_path())
            if self._file_writer.file_exists(sidecar) and not self._overwrite:
                self.signals.exists.emit(path, sidecar)
                return

            if not self._file_writer.write_file_bytes(sidecar, data):
                self.signals.failed.emit(path, "Could not write subtitle to NAS")
                return

            self._saved_state.mark_saved_to_nas(path)
            self.signals.finished.emit(path, sidecar)
        except Exception as exc:
            self.signals.failed.emit(path, str(exc))


class _NapiSaveSignals(QObject):
    finished = Signal(object, object)
    exists = Signal(object, object)
    failed = Signal(object, str)
