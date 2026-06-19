"""Parallel SMB library builder."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import PurePosixPath

from lumi.domain.filesystem.files_lister import DirectoryEntry, FilesLister
from lumi.domain.library.build_progress import LibraryBuildProgress, LibraryProgressCallback
from lumi.domain.library.building.library_parser import LibraryParser
from lumi.domain.library.models import Library, LibraryEntry
from lumi.infrastructure.smb.smb_file_repository import SmbFileRepository

logger = logging.getLogger(__name__)

DEFAULT_MAX_WORKERS = 8


class SmbLibraryBuilder:
    def __init__(
        self,
        file_lister: FilesLister,
        library_parser: LibraryParser,
        *,
        max_workers: int = DEFAULT_MAX_WORKERS,
    ) -> None:
        self._file_lister = file_lister
        self._library_parser = library_parser
        self._max_workers = max_workers

    def build_library_from(
        self,
        root_library_path: PurePosixPath,
        progress: LibraryProgressCallback | None = None,
    ) -> Library:
        logger.info("Listing the root library directory")
        root_dirs = [
            entry
            for entry in self._file_lister.list_files_and_directories(root_library_path)
            if entry.is_directory
        ]
        total = len(root_dirs)

        logger.info("Building the library from %d top-level directories", total)
        if progress is not None:
            progress(LibraryBuildProgress(completed=0, total=total))

        if total == 0:
            return Library(entries=[])

        entries: list[LibraryEntry] = []
        progress_lock = threading.Lock()
        completed = 0

        try:
            worker_count = min(self._max_workers, total)
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(self._parse_directory, directory): directory for directory in root_dirs
                }
                for future in as_completed(futures):
                    directory = futures[future]
                    parsed_entry = future.result()
                    if parsed_entry is not None:
                        entries.append(parsed_entry)
                    if progress is not None:
                        with progress_lock:
                            completed += 1
                            progress(
                                LibraryBuildProgress(
                                    completed=completed,
                                    total=total,
                                    directory_name=directory.name,
                                )
                            )
        finally:
            if isinstance(self._file_lister, SmbFileRepository):
                self._file_lister.disconnect_extra_sessions()

        logger.info("Library built with %d entries", len(entries))
        return Library(entries=entries)

    def _parse_directory(self, directory: DirectoryEntry) -> LibraryEntry | None:
        return self._library_parser.parse_directory(directory)
