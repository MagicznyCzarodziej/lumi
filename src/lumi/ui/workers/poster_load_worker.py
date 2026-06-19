"""Background poster fetch worker."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from lumi.domain.poster.image_file_poster_provider import ImageFilePosterProvider
from lumi.domain.poster.poster_cache import PosterCache


class PosterLoadWorker(QRunnable):
    """Reads poster bytes from disk cache or SMB (never copies video files)."""

    def __init__(
        self,
        poster_path: PurePosixPath,
        poster_provider: ImageFilePosterProvider,
        poster_cache: PosterCache,
    ) -> None:
        super().__init__()
        self.poster_path = poster_path
        self._poster_provider = poster_provider
        self._poster_cache = poster_cache
        self.signals = _PosterLoadSignals()

    @Slot()
    def run(self) -> None:
        path = self.poster_path
        try:
            cached = self._poster_cache.read(path)
            if cached is not None:
                self.signals.finished.emit(path, cached)
                return

            data = self._poster_provider.fetch_poster_bytes(path)
            self._poster_cache.write(path, data)
            self.signals.finished.emit(path, data)
        except Exception as exc:
            self.signals.failed.emit(path, str(exc))


class _PosterLoadSignals(QObject):
    finished = Signal(object, object)
    failed = Signal(object, str)
