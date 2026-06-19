"""Library build progress reporting."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class LibraryBuildProgress:
    completed: int
    total: int
    directory_name: str | None = None


LibraryProgressCallback = Callable[[LibraryBuildProgress], None]
