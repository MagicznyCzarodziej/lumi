"""Local subtitle cache protocol."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Protocol


class SubtitleCache(Protocol):
    def contains(self, video_path: PurePosixPath) -> bool: ...

    def read(self, video_path: PurePosixPath) -> bytes | None: ...

    def write(self, video_path: PurePosixPath, data: bytes) -> Path: ...

    def delete(self, video_path: PurePosixPath) -> None: ...

    def local_path(self, video_path: PurePosixPath) -> Path | None: ...
