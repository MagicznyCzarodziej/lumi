"""Debounced async poster loading for PosterWidget."""

from __future__ import annotations

from pathlib import PurePosixPath

from collections import OrderedDict

from PySide6.QtCore import QObject, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QPixmap

from lumi.domain.poster.image_file_poster_provider import ImageFilePosterProvider
from lumi.domain.poster.poster_cache import PosterCache
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
        self._pending_debounce: tuple[PurePosixPath, int] | None = None
        self._load_generations: dict[str, int] = {}
        self._workers: list[PosterLoadWorker] = []
        self._memory_cache: OrderedDict[str, QPixmap] = OrderedDict()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_debounced_load)

    def load(self, poster_path: PurePosixPath | None, *, immediate: bool = False) -> bool:
        """Load a poster. Returns True when handled synchronously from memory cache."""
        self._timer.stop()
        if poster_path is None:
            self._pending_debounce = None
            self.cleared.emit()
            return True

        cache_key = poster_path.as_posix()
        memory_cached = self._memory_cache.get(cache_key)
        if memory_cached is not None and not memory_cached.isNull():
            self._memory_cache.move_to_end(cache_key)
            self.loaded.emit(poster_path, memory_cached)
            return True

        generation = self._bump_generation(cache_key)
        if immediate or self._poster_cache.contains(poster_path):
            self._start_load_worker(poster_path, generation)
            return False

        self._pending_debounce = (poster_path, generation)
        self._timer.start(self._debounce_ms)
        return False

    def _bump_generation(self, cache_key: str) -> int:
        generation = self._load_generations.get(cache_key, 0) + 1
        self._load_generations[cache_key] = generation
        return generation

    def _start_debounced_load(self) -> None:
        pending = self._pending_debounce
        if pending is None:
            return
        poster_path, generation = pending
        cache_key = poster_path.as_posix()
        if generation != self._load_generations.get(cache_key):
            return
        self._start_load_worker(poster_path, generation)

    def _start_load_worker(self, poster_path: PurePosixPath, generation: int) -> None:
        worker = PosterLoadWorker(poster_path, self._poster_provider, self._poster_cache)
        self._workers.append(worker)
        worker.signals.finished.connect(
            lambda path, image, gen=generation: self._on_finished(path, image, gen),
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
    def _on_finished(self, poster_path: PurePosixPath, image: QImage, generation: int) -> None:
        cache_key = poster_path.as_posix()
        if generation != self._load_generations.get(cache_key):
            return
        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            self.failed.emit(poster_path, "Invalid image data")
            return
        self._remember_in_memory_cache(cache_key, pixmap)
        self.loaded.emit(poster_path, pixmap)

    @Slot(object, str, int)
    def _on_failed(self, poster_path: PurePosixPath, message: str, generation: int) -> None:
        cache_key = poster_path.as_posix()
        if generation != self._load_generations.get(cache_key):
            return
        self.failed.emit(poster_path, message)

    def _remember_in_memory_cache(self, cache_key: str, pixmap: QPixmap) -> None:
        self._memory_cache[cache_key] = pixmap
        self._memory_cache.move_to_end(cache_key)
        while len(self._memory_cache) > self._MEMORY_CACHE_MAX:
            self._memory_cache.popitem(last=False)
