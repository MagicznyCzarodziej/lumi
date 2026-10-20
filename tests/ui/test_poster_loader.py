"""PosterLoader cache fast-path tests."""

from __future__ import annotations

from pathlib import PurePosixPath

import base64

from lumi.domain.poster.image_file_poster_provider import ImageFilePosterProvider
from lumi.infrastructure.poster_cache.disk_poster_cache import DiskPosterCache
from lumi.ui.poster_loader import PosterLoader
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class _UnusedPosterProvider(ImageFilePosterProvider):
    def __init__(self) -> None:
        super().__init__(
            file_repository=None,  # type: ignore[arg-type]
            files_lister=None,  # type: ignore[arg-type]
            poster_file_name="poster",
            supported_file_extensions={".jpg"},
        )


def _wait_for_loaded(loader: PosterLoader, timeout_ms: int = 1000) -> None:
    loop = QEventLoop()
    QTimer.singleShot(timeout_ms, loop.quit)
    loader.loaded.connect(lambda *_args: loop.quit())
    loader.failed.connect(lambda *_args: loop.quit())
    loop.exec()


def test_poster_loader_disk_cache_loads_asynchronously(tmp_path) -> None:
    QApplication.instance() or QApplication([])
    poster_path = PurePosixPath("Alien")
    disk_cache = DiskPosterCache(tmp_path)
    disk_cache.write(poster_path, TINY_PNG)

    loader = PosterLoader(_UnusedPosterProvider(), disk_cache)
    received: list[PurePosixPath] = []
    loader.loaded.connect(lambda path, _pixmap: received.append(path))

    assert loader.load(poster_path) is False
    _wait_for_loaded(loader)
    assert received == [poster_path]


def test_poster_loader_loads_multiple_paths_without_cancelling(tmp_path) -> None:
    QApplication.instance() or QApplication([])
    first_path = PurePosixPath("Alien")
    second_path = PurePosixPath("Blade Runner")
    disk_cache = DiskPosterCache(tmp_path)
    disk_cache.write(first_path, TINY_PNG)
    disk_cache.write(second_path, TINY_PNG)

    loader = PosterLoader(_UnusedPosterProvider(), disk_cache)
    received: list[PurePosixPath] = []
    loader.loaded.connect(lambda path, _pixmap: received.append(path))

    assert loader.load(first_path, immediate=True) is False
    assert loader.load(second_path, immediate=True) is False

    loop = QEventLoop()
    QTimer.singleShot(2000, loop.quit)
    loader.loaded.connect(
        lambda *_args: loop.quit() if len({*received}) >= 2 else None,
    )
    loop.exec()

    assert first_path in received
    assert second_path in received


def test_poster_loader_memory_cache_is_synchronous(tmp_path) -> None:
    QApplication.instance() or QApplication([])
    poster_path = PurePosixPath("Alien")
    disk_cache = DiskPosterCache(tmp_path)
    disk_cache.write(poster_path, TINY_PNG)
    loader = PosterLoader(_UnusedPosterProvider(), disk_cache)
    loader.load(poster_path)
    _wait_for_loaded(loader)

    disk_cache.write(poster_path, b"stale-should-not-be-read")

    received: list[PurePosixPath] = []
    loader.loaded.connect(lambda path, _pixmap: received.append(path))

    assert loader.load(poster_path) is True
    assert received == [poster_path]
