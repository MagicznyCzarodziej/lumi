"""Partial file read access for video hashing."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol


class VideoRangeReader(Protocol):
    def read_file_range(self, absolute_path: PurePosixPath, offset: int, length: int) -> bytes | None: ...
