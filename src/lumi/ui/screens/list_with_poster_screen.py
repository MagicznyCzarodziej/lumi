"""Base screen using ListWithPosterLayout."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout

from lumi.ui.layouts.list_with_poster_layout import ListWithPosterLayout, ListWithPosterViewState
from lumi.ui.navigation.navigable_screen import NavigableScreen


class ListWithPosterScreen(NavigableScreen):
    def __init__(self, layout: ListWithPosterLayout) -> None:
        super().__init__()
        self._layout = layout

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._layout, stretch=1)

        entries = self._layout.entries_list
        entries.focus_left_requested.connect(self.back_requested.emit)
        entries.back_requested.connect(self.back_requested.emit)

    def apply_state(self, state: ListWithPosterViewState | None) -> None:
        self._layout.apply_state(state)

    def focus_default(self) -> None:
        entries = self._layout.entries_list
        entries.scroll_to_row(entries.focused_row())
        entries.setFocus(Qt.FocusReason.OtherFocusReason)

    def focus_playback_path(self, path: PurePosixPath) -> bool:
        if not self._layout.entries_list.focus_playback_path(path):
            return False
        self.focus_default()
        return True
