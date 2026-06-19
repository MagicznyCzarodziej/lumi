"""Poster provider tests."""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.domain.poster.image_file_poster_provider import (
    ImageFilePosterProvider,
    PosterImageNotFound,
    is_placeholder_poster_path,
)


class _FakeRepo:
    def __init__(self, *, files: dict[PurePosixPath, bytes] | None = None) -> None:
        self.files = files or {}

    def use_read_file_stream(self, absolute_path: PurePosixPath, block):
        data = self.files.get(absolute_path)
        if data is None:
            return None
        return block(iter([data]))


class _FakeLister:
    def __init__(self, entries: dict[PurePosixPath, list[DirectoryEntry]]) -> None:
        self.entries = entries

    def list_files_and_directories(self, directory_absolute_path: PurePosixPath) -> list[DirectoryEntry]:
        return self.entries.get(directory_absolute_path, [])


def test_is_placeholder_poster_path() -> None:
    assert is_placeholder_poster_path(PurePosixPath("defaultPoster.jpg"))
    assert not is_placeholder_poster_path(PurePosixPath("Alien"))


def test_fetch_poster_bytes_resolves_directory() -> None:
    directory = PurePosixPath("Alien")
    poster_file = directory / "poster.jpg"
    provider = ImageFilePosterProvider(
        file_repository=_FakeRepo(files={poster_file: b"image-bytes"}),
        files_lister=_FakeLister(
            {
                directory: [
                    DirectoryEntry(
                        name="poster.jpg",
                        absolute_path=poster_file,
                        is_directory=False,
                        is_file=True,
                    )
                ]
            }
        ),
        poster_file_name="poster",
        supported_file_extensions={".jpg"},
    )

    assert provider.fetch_poster_bytes(directory) == b"image-bytes"


def test_fetch_poster_bytes_missing_poster_raises() -> None:
    directory = PurePosixPath("Alien")
    provider = ImageFilePosterProvider(
        file_repository=_FakeRepo(),
        files_lister=_FakeLister({directory: []}),
        poster_file_name="poster",
        supported_file_extensions={".jpg"},
    )

    with pytest.raises(PosterImageNotFound):
        provider.fetch_poster_bytes(directory)
