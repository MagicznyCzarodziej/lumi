"""Mock file access — no-op filesystem for mock mode."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import PurePosixPath
from typing import TypeVar

from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.files_lister import DirectoryEntry, FilesLister

T = TypeVar("T")


class MockFileRepository(FilesLister, FileRepository):
    def list_files_and_directories(self, directory_absolute_path: PurePosixPath) -> list[DirectoryEntry]:
        return []

    def use_read_file_stream(
        self,
        absolute_path: PurePosixPath,
        block: Callable[[Iterator[bytes]], T],
    ) -> T | None:
        return None
