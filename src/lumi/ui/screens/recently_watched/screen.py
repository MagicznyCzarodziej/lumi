"""First-class Recently Watched destination."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from lumi.ui.components.poster_widget import PosterWidget
from lumi.ui.components.recent_watch_header import RecentWatchHeader
from lumi.ui.components.recent_watch_list import RecentWatchList
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.destinations import Destination, LIBRARY, RecentlyWatchedDestination
from lumi.ui.navigation.navigable_screen import NavigableScreen
from lumi.ui.navigation.router import Router
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.screens.recently_watched.controller import build_recently_watched_state
from lumi.ui.theme.spacing import (
    LIST_CONTENT_MARGINS,
    LIST_HEADER_SECTION_GAP,
    LIST_LAYOUT_STRETCH,
    POSTER_COLUMN_WIDTH,
    POSTER_CONTENT_GAP,
)
from lumi.ui.theme.styles import apply_widget_stylesheet


class RecentlyWatchedScreen(NavigableScreen):
    """Displays resumable media and always returns to the Library root."""

    def __init__(
        self,
        router: Router,
        *,
        poster_loader: PosterLoader | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RecentlyWatchedScreen")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self._router = router
        self._poster_loader = poster_loader
        self._poster = PosterWidget()
        self._poster.setFixedWidth(POSTER_COLUMN_WIDTH)
        self._header = RecentWatchHeader()
        self._rows = RecentWatchList()
        if poster_loader is not None:
            self._poster.bind_loader(poster_loader)
            self._rows.bind_poster_loader(poster_loader)
        self._empty_label = QLabel("No recently watched videos.")
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()

        main_column = QWidget()
        main_layout = QVBoxLayout(main_column)
        main_layout.setContentsMargins(*LIST_CONTENT_MARGINS)
        main_layout.setSpacing(LIST_HEADER_SECTION_GAP)
        main_layout.addWidget(self._header)
        main_layout.addWidget(self._empty_label)
        main_layout.addWidget(self._rows, stretch=1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(POSTER_CONTENT_GAP)
        layout.addWidget(self._poster)
        layout.addWidget(main_column, stretch=LIST_LAYOUT_STRETCH)

        self._rows.back_requested.connect(self._return_to_library)
        self._rows.currentRowChanged.connect(self._sync_feature_poster)

    @property
    def header(self) -> RecentWatchHeader:
        return self._header

    @property
    def rows(self) -> RecentWatchList:
        return self._rows

    @property
    def poster(self) -> PosterWidget:
        return self._poster

    def bind(self, destination: Destination, context: ScreenContext) -> None:
        if not isinstance(destination, RecentlyWatchedDestination):
            return
        self.reload(context)

    def reload(self, context: ScreenContext) -> None:
        """Rebuild rows from persisted watch history (e.g. after closing the player)."""
        focus_path = None
        if current := self._rows.current_row_widget():
            focus_path = current.model.playback_path
        state = build_recently_watched_state(
            context.watch_history.recent_entries(),
            context.library_repository.get_top_level_entries(),
            self._router,
            context.video_player,
            watch_history=context.watch_history,
            on_entry_removed=lambda: self.reload(context),
        )
        self._rows.set_rows(state.rows)
        self._empty_label.setVisible(not state.rows)
        self._rows.setVisible(bool(state.rows))
        if focus_path is not None:
            self._rows.focus_playback_path(focus_path)
        self._sync_feature_poster(self._rows.currentRow())

    def focus_default(self) -> None:
        if self._rows.entry_count:
            self._rows.setFocus(Qt.FocusReason.OtherFocusReason)
            return

    def focus_playback_path(self, path: PurePosixPath) -> bool:
        return self._rows.focus_playback_path(path)

    def _sync_feature_poster(self, row: int) -> None:
        widget = self._rows.current_row_widget()
        if widget is None:
            self._poster.set_poster_path(None, immediate=True)
            return
        self._poster.set_poster_path(widget.model.poster_path, immediate=True)

    def _return_to_library(self) -> None:
        self._router.reset_to(LIBRARY)
