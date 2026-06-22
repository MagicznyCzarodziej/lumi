"""File write access."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol


class FileWriter(Protocol):
    def file_exists(self, absolute_path: PurePosixPath) -> bool: ...

    def write_file_bytes(self, absolute_path: PurePosixPath, data: bytes) -> bool: ...
