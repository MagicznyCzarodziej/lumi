"""Keyboard-first list of recently watched A3 play rows."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFocusEvent, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QWidget,
)

from lumi.ui.components.keyboard_helpers import is_escape_key
from lumi.ui.components.recent_watch_row import RecentWatchRow
from lumi.ui.screens.recently_watched.controller import RecentWatchRowUiModel
from lumi.ui.theme.spacing import RECENT_WATCH_ROW_SPACING, RECENT_WATCH_THUMBNAIL_HEIGHT
from lumi.ui.theme.styles import apply_widget_stylesheet


class RecentWatchList(QListWidget):
    """A list that keeps action selection in the current row."""

    back_requested = Signal()
    focus_up_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RecentWatchList")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSpacing(RECENT_WATCH_ROW_SPACING)
        self._rows: list[RecentWatchRow] = []
        self.currentRowChanged.connect(lambda _row: self._sync_row_focus())

    def set_rows(self, rows: list[RecentWatchRowUiModel]) -> None:
        self.clear()
        self._rows = []
        for model in rows:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, RECENT_WATCH_THUMBNAIL_HEIGHT))
            self.addItem(item)
            row = RecentWatchRow(model)
            self.setItemWidget(item, row)
            self._rows.append(row)
        if rows:
            self.setCurrentRow(0)
        self._sync_row_focus()

    def focus_playback_path(self, path: PurePosixPath) -> bool:
        for index, row in enumerate(self._rows):
            if row.model.playback_path == path:
                self.setCurrentRow(index)
                self.scrollToItem(
                    self.item(index),
                    QAbstractItemView.ScrollHint.PositionAtCenter,
                )
                self.setFocus(Qt.FocusReason.OtherFocusReason)
                return True
        return False

    def current_row_widget(self) -> RecentWatchRow | None:
        row = self.currentRow()
        if row < 0 or row >= len(self._rows):
            return None
        return self._rows[row]

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        self._sync_row_focus()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        self._sync_row_focus()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if is_escape_key(event.key()):
            self.back_requested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Left:
            if row := self.current_row_widget():
                row.move_action(-1)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Right:
            if row := self.current_row_widget():
                row.move_action(1)
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if row := self.current_row_widget():
                row.activate_selected_action()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Up and self.currentRow() <= 0:
            self.focus_up_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def _sync_row_focus(self) -> None:
        current_row = self.currentRow()
        has_focus = self.hasFocus()
        for index, row in enumerate(self._rows):
            row.set_row_focused(has_focus and index == current_row)
