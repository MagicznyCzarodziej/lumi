"""Library builder interface."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol

from lumi.domain.library.build_progress import LibraryProgressCallback
from lumi.domain.library.models import Library


class LibraryBuilder(Protocol):
    def build_library_from(
        self,
        root_library_path: PurePosixPath,
        progress: LibraryProgressCallback | None = None,
    ) -> Library: ...
