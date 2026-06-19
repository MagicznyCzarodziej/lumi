"""Per-directory YAML config models."""

from __future__ import annotations

from enum import Enum

from lumi.domain.library.models import Franchise


class LumiDirectoryConfigType(Enum):
    FILM_SERIES = "FILM_SERIES"


class LumiDirectoryConfig:
    def __init__(
        self,
        type: LumiDirectoryConfigType | None,
        franchise: Franchise | None,
        tags: set[str],
    ) -> None:
        self.type = type
        self.franchise = franchise
        self.tags = tags
