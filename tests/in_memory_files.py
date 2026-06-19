"""In-memory filesystem tree for domain/infrastructure tests."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import PurePosixPath
from typing import TypeVar

from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.files_lister import DirectoryEntry, FilesLister

T = TypeVar("T")


class InMemoryFileTree(FilesLister, FileRepository):
    def __init__(self) -> None:
        self._children: dict[PurePosixPath, list[DirectoryEntry]] = {}
        self._file_bytes: dict[PurePosixPath, bytes] = {}

    def add_directory(self, path: PurePosixPath) -> None:
        self._ensure_parent(path)
        self._children.setdefault(path, [])
        parent = PurePosixPath(*path.parts[:-1]) if len(path.parts) > 1 else PurePosixPath(".")
        entry = DirectoryEntry(name=path.name, absolute_path=path, is_directory=True, is_file=False)
        siblings = self._children.setdefault(parent, [])
        if not any(existing.absolute_path == path for existing in siblings):
            siblings.append(entry)

    def add_file(self, path: PurePosixPath, *, data: bytes = b"") -> None:
        parent = PurePosixPath(*path.parts[:-1]) if len(path.parts) > 1 else PurePosixPath(".")
        self._ensure_parent(parent)
        name = path.name
        entry = DirectoryEntry(name=name, absolute_path=path, is_directory=False, is_file=True)
        children = self._children.setdefault(parent, [])
        if not any(existing.absolute_path == path for existing in children):
            children.append(entry)
        self._file_bytes[path] = data

    def list_files_and_directories(self, directory_absolute_path: PurePosixPath) -> list[DirectoryEntry]:
        return list(self._children.get(directory_absolute_path, []))

    def use_read_file_stream(
        self,
        absolute_path: PurePosixPath,
        block: Callable[[Iterator[bytes]], T],
    ) -> T | None:
        data = self._file_bytes.get(absolute_path)
        if data is None:
            return None
        return block(iter([data]))

    def _ensure_parent(self, path: PurePosixPath) -> None:
        if len(path.parts) <= 1:
            return
        parent = PurePosixPath(*path.parts[:-1])
        if parent not in self._children:
            self._children[parent] = []
            self._ensure_parent(parent)
            parent_name = parent.name
            grandparent = PurePosixPath(*parent.parts[:-1]) if len(parent.parts) > 1 else PurePosixPath(".")
            entry = DirectoryEntry(
                name=parent_name,
                absolute_path=parent,
                is_directory=True,
                is_file=False,
            )
            siblings = self._children.setdefault(grandparent, [])
            if not any(existing.absolute_path == parent for existing in siblings):
                siblings.append(entry)
