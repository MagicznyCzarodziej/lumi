"""Mock file access — no-op filesystem for mock mode."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import PurePosixPath
from typing import TypeVar

from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.files_lister import DirectoryEntry, FilesLister

T = TypeVar("T")


class MockFileRepository(FilesLister, FileRepository):
    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    def seed_file(self, absolute_path: PurePosixPath, data: bytes) -> None:
        self._files[absolute_path.as_posix()] = data

    def list_files_and_directories(self, directory_absolute_path: PurePosixPath) -> list[DirectoryEntry]:
        return []

    def use_read_file_stream(
        self,
        absolute_path: PurePosixPath,
        block: Callable[[Iterator[bytes]], T],
    ) -> T | None:
        data = self._files.get(absolute_path.as_posix())
        if data is None:
            return None

        def chunks() -> Iterator[bytes]:
            yield data

        return block(chunks())

    def file_exists(self, absolute_path: PurePosixPath) -> bool:
        return absolute_path.as_posix() in self._files

    def read_file_range(self, absolute_path: PurePosixPath, offset: int, length: int) -> bytes | None:
        data = self._files.get(absolute_path.as_posix())
        if data is None:
            return None
        return data[offset : offset + length]

    def write_file_bytes(self, absolute_path: PurePosixPath, data: bytes) -> bool:
        self._files[absolute_path.as_posix()] = data
        return True
