"""First-class Recently Watched destination."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path, PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from lumi.domain.recent_watch import RecentWatchRecord
from lumi.ui.components.recent_watch_header import RecentWatchHeader
from lumi.ui.components.recent_watch_list import RecentWatchList
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.destinations import Destination, LIBRARY, RecentlyWatchedDestination
from lumi.ui.navigation.navigable_screen import NavigableScreen
from lumi.ui.navigation.router import Router
from lumi.ui.screens.recently_watched.controller import build_recently_watched_state
from lumi.ui.theme.spacing import CONTENT_INSET, SPACE_MD
from lumi.ui.theme.styles import apply_widget_stylesheet

RecentWatchRecordsLoader = Callable[[], list[RecentWatchRecord]]


class RecentlyWatchedScreen(NavigableScreen):
    """Displays resumable media and always returns to the Library root."""

    def __init__(
        self,
        router: Router,
        *,
        records_loader: RecentWatchRecordsLoader,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RecentlyWatchedScreen")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self._router = router
        self._records_loader = records_loader
        self._header = RecentWatchHeader()
        self._rows = RecentWatchList()
        self._empty_label = QLabel("No recently watched videos.")
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(CONTENT_INSET, CONTENT_INSET, CONTENT_INSET, CONTENT_INSET)
        layout.setSpacing(SPACE_MD)
        layout.addWidget(self._header)
        layout.addWidget(self._rows, stretch=1)
        layout.addWidget(self._empty_label, stretch=1)

        self._header.activated.connect(self._return_to_library)
        self._rows.back_requested.connect(self._return_to_library)
        self._rows.focus_up_requested.connect(self._focus_header)

    @property
    def header(self) -> RecentWatchHeader:
        return self._header

    @property
    def rows(self) -> RecentWatchList:
        return self._rows

    def bind(self, destination: Destination, context: ScreenContext) -> None:
        if not isinstance(destination, RecentlyWatchedDestination):
            return
        state = build_recently_watched_state(
            self._records_loader(),
            context.library_repository.get_top_level_entries(),
            self._router,
            context.video_player,
        )
        self._rows.set_rows(state.rows)
        self._empty_label.setVisible(not state.rows)
        self._rows.setVisible(bool(state.rows))

    def focus_default(self) -> None:
        if self._rows.count():
            self._rows.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        self._focus_header()

    def focus_playback_path(self, path: PurePosixPath) -> bool:
        return self._rows.focus_playback_path(path)

    def _focus_header(self) -> None:
        self._header.setFocus(Qt.FocusReason.OtherFocusReason)

    def _return_to_library(self) -> None:
        self._router.reset_to(LIBRARY)
