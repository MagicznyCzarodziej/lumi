from __future__ import annotations

from pathlib import PurePosixPath


def _path(value: str) -> PurePosixPath:
    return PurePosixPath(value)
