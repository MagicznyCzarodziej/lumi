"""Library cache interface."""

from __future__ import annotations

from typing import Protocol

from lumi.domain.library.models import Library


class LibraryCache(Protocol):
    def save(self, library: Library) -> bool: ...

    def load(self) -> Library | None: ...
