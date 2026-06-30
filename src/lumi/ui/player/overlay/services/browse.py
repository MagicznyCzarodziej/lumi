from __future__ import annotations

import logging
from pathlib import PurePosixPath

from PySide6.QtCore import Qt, QTimer

from lumi.domain.subtitles.browse import BrowseEntryKind, BrowseRow, parent_directory, share_path
from lumi.ui.player.overlay.state import View, close_subtitle_browse, open_subtitle_browse
from lumi.ui.player.overlay.services.base import OverlayService
from lumi.ui.workers.directory_list_worker import DirectoryListWorker

logger = logging.getLogger(__name__)


class BrowseService(OverlayService):
    def _default_browse_directory(self) -> PurePosixPath | None:
        if self._rt.library_path is not None:
            if self._rt.deps.playback_uri_resolver is not None:
                try:
                    resolved = self._rt.deps.playback_uri_resolver.resolve_path(self._rt.library_path)
                    return share_path(resolved.parent if resolved.name else resolved)
                except OSError:
                    pass
            if self._rt.library_path.name:
                return share_path(self._rt.library_path.parent)
            return share_path(self._rt.library_path)
        if self._rt.deps.library_root is not None and str(self._rt.deps.library_root).strip("/"):
            return share_path(self._rt.deps.library_root)
        return None

    def open(self) -> None:
        directory = self._default_browse_directory()
        if directory is None or self._rt.deps.files_lister is None:
            return
        self._o.show()
        self._o.raise_()
        self._rt.state = open_subtitle_browse(self._rt.state)
        self._rt.hide_timer.stop()
        self._rt.dim_timer.stop()
        self._rt.ui_opacity = 1.0
        self.load_directory(directory)

    def close(self) -> None:
        self._rt.browse_target = None
        self._rt.browse_busy = False
        self._rt.state = close_subtitle_browse(self._rt.state)
        self._o.tracks.refresh_rows()
        self._o.panel.rebuild()
        self._o.activity.note_ui_activity()
        self._update()

    def load_directory(self, directory: PurePosixPath) -> None:
        if self._rt.deps.files_lister is None:
            return
        self._rt.browse_target = share_path(directory)
        self._rt.state.browse_path = self._rt.browse_target
        self._rt.state.browse_rows = []
        self._update()
        if self._rt.browse_busy:
            return
        self._start_browse_worker()

    def _start_browse_worker(self) -> None:
        if self._rt.browse_busy or self._rt.deps.files_lister is None:
            return
        target = self._rt.browse_target
        if target is None or self._rt.state.view != View.SUBTITLE_BROWSE:
            return
        self._rt.browse_busy = True
        worker = DirectoryListWorker(
            self._rt.deps.files_lister,
            target,
            set(self._rt.deps.subtitle_extensions),
            library_root=self._rt.deps.library_root,
        )
        worker.signals.finished.connect(
            self._o._worker_slots.browse_loaded,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.failed.connect(
            self._o._worker_slots.browse_failed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._rt.thread_pool.start(worker)

    def on_browse_loaded(
        self,
        requested: PurePosixPath,
        resolved: PurePosixPath,
        rows: list[BrowseRow],
    ) -> None:
        self._rt.browse_busy = False
        if self._rt.state.view != View.SUBTITLE_BROWSE:
            return
        if self._rt.browse_target is not None and share_path(requested) != self._rt.browse_target:
            self._start_browse_worker()
            return
        self._rt.state.browse_path = share_path(resolved)
        self._rt.state.browse_rows = list(rows)
        if self._rt.state.browse_rows:
            self._rt.state.browse_focus = max(
                0, min(self._rt.state.browse_focus, len(self._rt.state.browse_rows) - 1)
            )
        else:
            self._rt.state.browse_focus = 0
        self._o.panel.rebuild()
        self._o.panel.ensure_panel_focus_visible()
        self._update()
        if self._rt.browse_target is not None and share_path(resolved) != self._rt.browse_target:
            self._start_browse_worker()

    def on_browse_failed(
        self,
        directory: PurePosixPath,
        message: str,
    ) -> None:
        self._rt.browse_busy = False
        if self._rt.state.view != View.SUBTITLE_BROWSE:
            return
        if self._rt.browse_target is not None and share_path(directory) != self._rt.browse_target:
            self._start_browse_worker()
            return
        logger.warning("Browse directory failed for %s: %s", directory, message)
        parent = parent_directory(share_path(directory))
        self._rt.state.browse_rows = (
            [BrowseRow(label="..", path=parent, kind=BrowseEntryKind.PARENT)] if parent else []
        )
        self._o.panel.rebuild()
        self._update()
        if self._rt.browse_target is not None and share_path(directory) != self._rt.browse_target:
            self._start_browse_worker()

    def back(self) -> None:
        path = self._rt.state.browse_path
        if path is None:
            self._o.browse.close()
            return
        parent = parent_directory(path)
        if parent is None:
            self._o.browse.close()
        else:
            self._o.browse.load_directory(parent)

    def activate_row(self, index: int) -> None:
        rows = self._rt.state.browse_rows or []
        if index < 0 or index >= len(rows):
            return
        row = rows[index]
        if row.kind == BrowseEntryKind.SUBTITLE:
            self._o.browse.close()
            QTimer.singleShot(0, lambda path=row.path: self._o.subtitles.load_external(path))
        elif row.kind in (BrowseEntryKind.DIRECTORY, BrowseEntryKind.PARENT):
            self._rt.state.browse_focus = index
            self._o.browse.load_directory(row.path)
        self._o.activity.note_ui_activity()
