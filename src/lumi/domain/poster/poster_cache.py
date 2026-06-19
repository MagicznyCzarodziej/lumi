"""Poster byte cache interface."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol


class PosterCache(Protocol):
    def contains(self, poster_path: PurePosixPath) -> bool: ...

    def read(self, poster_path: PurePosixPath) -> bytes | None: ...

    def write(self, poster_path: PurePosixPath, data: bytes) -> object: ...
