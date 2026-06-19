"""Mock library repository — loads bundled mock_library.json fixture."""

from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath

from lumi.domain.library.build_progress import LibraryProgressCallback
from lumi.domain.library.library_repository import LibraryRepository
from lumi.domain.library.models import LibraryEntry
from lumi.domain.library.serialization import library_from_json
from lumi.domain.utils.library_sort import sort_library_entries

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "mock_library.json"


class MockLibraryRepository(LibraryRepository):
    def __init__(self, fixture_path: Path | None = None) -> None:
        self._fixture_path = fixture_path or DEFAULT_FIXTURE_PATH
        self._entries: list[LibraryEntry] = []

    def get_top_level_entries(self) -> list[LibraryEntry]:
        return self._entries

    def initialize(
        self,
        library_root_path: PurePosixPath,
        ignore_cache: bool = False,
        progress: LibraryProgressCallback | None = None,
    ) -> None:
        del library_root_path, ignore_cache, progress
        logger.debug("MockLibraryRepository: loading sample data from JSON")
        library = library_from_json(self._fixture_path.read_text(encoding="utf-8"))
        self._entries = sort_library_entries(library.entries)
