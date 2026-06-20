"""Poster load worker tests."""

from __future__ import annotations

from pathlib import PurePosixPath

import base64

from PySide6.QtGui import QImage

from lumi.domain.poster.image_file_poster_provider import ImageFilePosterProvider, is_placeholder_poster_path
from lumi.infrastructure.poster_cache.disk_poster_cache import DiskPosterCache
from lumi.ui.workers.poster_load_worker import PosterLoadWorker

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class _FakePosterProvider(ImageFilePosterProvider):
    def __init__(self, data: bytes) -> None:
        self._data = data
        super().__init__(
            file_repository=None,  # type: ignore[arg-type]
            files_lister=None,  # type: ignore[arg-type]
            poster_file_name="poster",
            supported_file_extensions={".jpg"},
        )

    def fetch_poster_bytes(self, directory_or_file_path: PurePosixPath) -> bytes:
        return self._data


def test_is_missing_poster_path() -> None:
    assert is_placeholder_poster_path(PurePosixPath("defaultPoster.jpg"))
    assert not is_placeholder_poster_path(PurePosixPath("Alien/poster.jpg"))


def test_poster_load_worker_uses_disk_cache(tmp_path) -> None:
    cache = DiskPosterCache(tmp_path)
    path = PurePosixPath("Alien")
    cache.write(path, TINY_PNG)

    worker = PosterLoadWorker(path, _FakePosterProvider(b"network"), cache)
    received: list[tuple[PurePosixPath, QImage]] = []
    worker.signals.finished.connect(lambda p, image: received.append((p, image)))
    worker.run()

    assert len(received) == 1
    assert received[0][0] == path
    assert not received[0][1].isNull()


def test_poster_load_worker_fetches_and_caches(tmp_path) -> None:
    cache = DiskPosterCache(tmp_path)
    path = PurePosixPath("Alien")

    worker = PosterLoadWorker(path, _FakePosterProvider(b"fresh"), cache)
    worker.run()

    assert cache.read(path) == b"fresh"


def test_poster_load_worker_missing_poster_emits_failed(tmp_path) -> None:
    cache = DiskPosterCache(tmp_path)
    path = PurePosixPath("defaultPoster.jpg")

    class _RaisingProvider(ImageFilePosterProvider):
        def __init__(self) -> None:
            super().__init__(
                file_repository=None,  # type: ignore[arg-type]
                files_lister=None,  # type: ignore[arg-type]
                poster_file_name="poster",
                supported_file_extensions={".jpg"},
            )

        def fetch_poster_bytes(self, directory_or_file_path: PurePosixPath) -> bytes:
            raise RuntimeError("missing")

    worker = PosterLoadWorker(path, _RaisingProvider(), cache)
    errors: list[str] = []
    worker.signals.failed.connect(lambda _path, message: errors.append(message))
    worker.run()

    assert errors
