"""Directory listing types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol


@dataclass(frozen=True)
class DirectoryEntry:
    name: str
    absolute_path: PurePosixPath
    is_directory: bool
    is_file: bool


class FilesLister(Protocol):
    def list_files_and_directories(self, directory_absolute_path: PurePosixPath) -> list[DirectoryEntry]: ...
