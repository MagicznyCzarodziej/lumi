"""Disk poster cache tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT

from pathlib import PurePosixPath

from lumi.infrastructure.poster_cache.disk_poster_cache import DiskPosterCache


def test_disk_poster_cache_round_trip(tmp_path) -> None:
    cache = DiskPosterCache(tmp_path / "posters")
    poster_path = MOCK_LIBRARY_ROOT / "Alien/poster.jpg"
    data = b"fake-image-bytes"

    assert cache.read(poster_path) is None
    cache.write(poster_path, data)
    assert cache.read(poster_path) == data
    assert cache.cache_file(poster_path).is_file()


def test_disk_poster_cache_contains(tmp_path) -> None:
    cache = DiskPosterCache(tmp_path)
    poster_path = PurePosixPath("Alien/poster.jpg")
    assert not cache.contains(poster_path)
    cache.write(poster_path, b"data")
    assert cache.contains(poster_path)


def test_disk_poster_cache_key_is_stable(tmp_path) -> None:
    cache = DiskPosterCache(tmp_path)
    path = MOCK_LIBRARY_ROOT / "Alien/poster.jpg"
    assert cache.cache_key(path) == cache.cache_key(path)
    assert cache.cache_key(path) != cache.cache_key(MOCK_LIBRARY_ROOT / "Alien/poster.png")
