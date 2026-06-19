"""In-memory library repository with JSON cache."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.library.build_progress import LibraryProgressCallback
from lumi.domain.library.building.library_builder import LibraryBuilder
from lumi.domain.library.entry_ordering import normalize_library
from lumi.domain.library.library_cache import LibraryCache
from lumi.domain.library.library_repository import LibraryRepository
from lumi.domain.library.models import Library, LibraryEntry
from lumi.domain.utils.library_sort import sort_library_entries


class InMemoryCachedLibraryRepository(LibraryRepository):
    def __init__(
        self,
        library_builder: LibraryBuilder,
        library_cache: LibraryCache,
    ) -> None:
        self._library_builder = library_builder
        self._library_cache = library_cache
        self._entries: list[LibraryEntry] = []
        self._last_cache_warning: str | None = None

    @property
    def last_cache_warning(self) -> str | None:
        return self._last_cache_warning

    def get_top_level_entries(self) -> list[LibraryEntry]:
        return self._entries

    def initialize(
        self,
        library_root_path: PurePosixPath,
        ignore_cache: bool = False,
        progress: LibraryProgressCallback | None = None,
    ) -> None:
        self._last_cache_warning = None
        library_from_cache = None if ignore_cache else self._library_cache.load()

        if library_from_cache is not None:
            self._entries = normalize_library(library_from_cache.entries)
            return

        library = self._library_builder.build_library_from(library_root_path, progress=progress)
        sorted_library = Library(entries=sort_library_entries(library.entries))
        normalized = Library(entries=normalize_library(sorted_library.entries))
        if not self._library_cache.save(normalized):
            self._last_cache_warning = "Could not save library cache to disk."
        self._entries = normalized.entries
