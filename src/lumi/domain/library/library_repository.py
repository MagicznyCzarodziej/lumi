"""Library repository interface."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol

from lumi.domain.library.build_progress import LibraryProgressCallback
from lumi.domain.library.models import LibraryEntry


class LibraryRepository(Protocol):
    def initialize(
        self,
        library_root_path: PurePosixPath,
        ignore_cache: bool = False,
        progress: LibraryProgressCallback | None = None,
    ) -> None: ...

    def get_top_level_entries(self) -> list[LibraryEntry]: ...
