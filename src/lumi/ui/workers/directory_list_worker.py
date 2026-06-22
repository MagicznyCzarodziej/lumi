"""Background SMB directory listing for subtitle browse."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from lumi.domain.filesystem.files_lister import FilesLister
from lumi.domain.subtitles.browse import BrowseRow, build_browse_rows, share_path


class DirectoryListWorker(QRunnable):
    """Lists a share directory off the UI thread."""

    def __init__(
        self,
        files_lister: FilesLister,
        directory: PurePosixPath,
        subtitle_extensions: set[str],
        *,
        library_root: PurePosixPath | None = None,
    ) -> None:
        super().__init__()
        self.directory = share_path(directory)
        self._files_lister = files_lister
        self._subtitle_extensions = subtitle_extensions
        self._library_root = share_path(library_root) if library_root else None
        self.signals = _DirectoryListSignals()

    @Slot()
    def run(self) -> None:
        try:
            rows, resolved = build_browse_rows(
                self._files_lister,
                self.directory,
                self._subtitle_extensions,
                library_root=self._library_root,
            )
            self.signals.finished.emit(self.directory, resolved, rows)
        except Exception as exc:
            self.signals.failed.emit(self.directory, str(exc))


class _DirectoryListSignals(QObject):
    finished = Signal(object, object, object)
    failed = Signal(object, str)
