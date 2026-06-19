"""Mock library builder — loads bundled JSON fixture."""

from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath

from lumi.domain.library.build_progress import LibraryBuildProgress, LibraryProgressCallback
from lumi.domain.library.models import Library
from lumi.domain.library.serialization import library_from_json

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "mock_library.json"


class MockLibraryBuilder:
    def __init__(self, fixture_path: Path | None = None) -> None:
        self._fixture_path = fixture_path or DEFAULT_FIXTURE_PATH

    def build_library_from(
        self,
        root_library_path: PurePosixPath,
        progress: LibraryProgressCallback | None = None,
    ) -> Library:
        del root_library_path
        logger.debug("MockLibraryBuilder: loading fixture from %s", self._fixture_path)
        if progress is not None:
            progress(LibraryBuildProgress(completed=0, total=1))
        library = library_from_json(self._fixture_path.read_text(encoding="utf-8"))
        if progress is not None:
            progress(LibraryBuildProgress(completed=1, total=1, directory_name="mock_library.json"))
        return library
