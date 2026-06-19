"""Debounced async poster loading for PosterWidget."""

from __future__ import annotations

from pathlib import PurePosixPath

from collections import OrderedDict

from PySide6.QtCore import QObject, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QPixmap

from lumi.domain.poster.image_file_poster_provider import ImageFilePosterProvider
from lumi.domain.poster.poster_cache import PosterCache
from lumi.ui.theme.spacing import POSTER_REFERENCE_HEIGHT, POSTER_REFERENCE_WIDTH
from lumi.ui.workers.poster_load_worker import PosterLoadWorker


class PosterLoader(QObject):
    loaded = Signal(object, object)
    failed = Signal(object, str)
    cleared = Signal()

    _MEMORY_CACHE_MAX = 64

    def __init__(
        self,
        poster_provider: ImageFilePosterProvider,
        poster_cache: PosterCache,
        *,
        debounce_ms: int = 300,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._poster_provider = poster_provider
        self._poster_cache = poster_cache
        self._debounce_ms = debounce_ms
        self._pool = QThreadPool.globalInstance()
        self._pending_path: PurePosixPath | None = None
        self._active_path: PurePosixPath | None = None
        self._generation = 0
        self._workers: list[PosterLoadWorker] = []
        self._memory_cache: OrderedDict[str, QPixmap] = OrderedDict()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_network_load)

    def load(self, poster_path: PurePosixPath | None) -> bool:
        """Load a poster. Returns True when handled synchronously from cache."""
        self._timer.stop()
        if poster_path is None:
            self._pending_path = None
            self._active_path = None
            self._generation += 1
            self.cleared.emit()
            return True

        cache_key = poster_path.as_posix()
        memory_cached = self._memory_cache.get(cache_key)
        if memory_cached is not None and not memory_cached.isNull():
            self._memory_cache.move_to_end(cache_key)
            self._active_path = poster_path
            self.loaded.emit(poster_path, normalize_poster_pixmap(memory_cached))
            return True

        if self._poster_cache.contains(poster_path):
            data = self._poster_cache.read(poster_path)
            if data is not None and self._emit_loaded_from_bytes(poster_path, data):
                return True

        self._pending_path = poster_path
        self._timer.start(self._debounce_ms)
        return False

    def _start_network_load(self) -> None:
        poster_path = self._pending_path
        if poster_path is None:
            return

        self._active_path = poster_path
        self._generation += 1
        generation = self._generation

        worker = PosterLoadWorker(poster_path, self._poster_provider, self._poster_cache)
        self._workers.append(worker)
        worker.signals.finished.connect(
            lambda path, data, gen=generation: self._on_finished(path, data, gen),
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.failed.connect(
            lambda path, message, gen=generation: self._on_failed(path, message, gen),
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.finished.connect(
            lambda *_args, w=worker: self._release_worker(w),
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.failed.connect(
            lambda *_args, w=worker: self._release_worker(w),
            Qt.ConnectionType.QueuedConnection,
        )
        self._pool.start(worker)

    def _release_worker(self, worker: PosterLoadWorker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)

    @Slot(object, object, int)
    def _on_finished(self, poster_path: PurePosixPath, data: bytes, generation: int) -> None:
        if generation != self._generation or poster_path != self._active_path:
            return
        if not self._emit_loaded_from_bytes(poster_path, data):
            self.failed.emit(poster_path, "Invalid image data")

    @Slot(object, str, int)
    def _on_failed(self, poster_path: PurePosixPath, message: str, generation: int) -> None:
        if generation != self._generation or poster_path != self._active_path:
            return
        self.failed.emit(poster_path, message)

    def _emit_loaded_from_bytes(self, poster_path: PurePosixPath, data: bytes) -> bool:
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            return False
        pixmap = normalize_poster_pixmap(pixmap)
        self._remember_in_memory_cache(poster_path.as_posix(), pixmap)
        self._active_path = poster_path
        self.loaded.emit(poster_path, pixmap)
        return True

    def _remember_in_memory_cache(self, cache_key: str, pixmap: QPixmap) -> None:
        self._memory_cache[cache_key] = pixmap
        self._memory_cache.move_to_end(cache_key)
        while len(self._memory_cache) > self._MEMORY_CACHE_MAX:
            self._memory_cache.popitem(last=False)


def normalize_poster_pixmap(pixmap: QPixmap) -> QPixmap:
    """Crop every poster to the same 2:3 frame so swaps do not jump."""
    if pixmap.isNull():
        return pixmap
    scaled = pixmap.scaled(
        POSTER_REFERENCE_WIDTH,
        POSTER_REFERENCE_HEIGHT,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    if scaled.isNull():
        return pixmap
    x = max(0, (scaled.width() - POSTER_REFERENCE_WIDTH) // 2)
    return scaled.copy(x, 0, POSTER_REFERENCE_WIDTH, POSTER_REFERENCE_HEIGHT)
