"""Background worker for library initialization."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import QThread, Signal

from lumi.domain.library.build_progress import LibraryBuildProgress
from lumi.domain.library.library_repository import LibraryRepository


class LibraryInitWorker(QThread):
    finished_ok = Signal()
    failed = Signal(str)
    progress = Signal(int, int, str)
    cache_warning = Signal(str)

    def __init__(
        self,
        repository: LibraryRepository,
        library_root: PurePosixPath,
        *,
        ignore_cache: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._library_root = library_root
        self._ignore_cache = ignore_cache

    def run(self) -> None:
        try:
            self._repository.initialize(
                self._library_root,
                ignore_cache=self._ignore_cache,
                progress=self._emit_progress,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        warning = getattr(self._repository, "last_cache_warning", None)
        if warning:
            self.cache_warning.emit(str(warning))

        self.finished_ok.emit()

    def _emit_progress(self, update: LibraryBuildProgress) -> None:
        self.progress.emit(
            update.completed,
            update.total,
            update.directory_name or "",
        )
