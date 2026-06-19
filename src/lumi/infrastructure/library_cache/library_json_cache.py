"""JSON library cache."""

from __future__ import annotations

import logging
from pathlib import Path

from lumi.domain.library.library_cache import LibraryCache
from lumi.domain.library.models import Library
from lumi.domain.library.serialization import library_from_json, library_to_json

logger = logging.getLogger(__name__)


class LibraryJsonCache(LibraryCache):
    def __init__(self, cache_file: Path) -> None:
        self._cache_file = cache_file

    def save(self, library: Library) -> bool:
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(library_to_json(library), encoding="utf-8")
            logger.debug("Library saved to cache")
            return True
        except OSError:
            logger.exception("Error while saving library to cache")
            return False

    def load(self) -> Library | None:
        if not self._cache_file.is_file():
            logger.debug("Library cache file doesn't exist")
            return None

        try:
            library = library_from_json(self._cache_file.read_text(encoding="utf-8"))
            logger.debug("Library loaded from cache")
            return library
        except (OSError, ValueError, KeyError):
            logger.exception("Error while reading library from cache. Deleting cache file")
            try:
                self._cache_file.unlink(missing_ok=True)
            except OSError:
                logger.exception("Failed to delete corrupt cache file")
            return None
