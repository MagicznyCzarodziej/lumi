"""File read access."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import PurePosixPath
from typing import Protocol, TypeVar

T = TypeVar("T")


class FileRepository(Protocol):
    def use_read_file_stream(
        self,
        absolute_path: PurePosixPath,
        block: Callable[[Iterator[bytes]], T],
    ) -> T | None: ...
