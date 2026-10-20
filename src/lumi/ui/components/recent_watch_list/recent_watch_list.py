"""Keyboard-first list of recently watched A3 play rows."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFocusEvent, QKeyEvent, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QWidget,
)

from lumi.ui.components.keyboard_helpers import is_escape_key
from lumi.ui.components.recent_watch_list.recent_watch_row_delegate import RecentWatchRowDelegate
from lumi.ui.components.recent_watch_row import RecentWatchRow
from lumi.ui.components.scroll_edge_fades import ScrollEdgeFadeOverlay
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.screens.recently_watched.controller import RecentWatchRowUiModel
from lumi.ui.theme.spacing import (
    CONTENT_INSET,
    LIST_ROW_VERTICAL_INSET,
    LIST_ROWS_FROM_TOP,
    RECENT_WATCH_LIST_VIEWPORT_MARGINS,
    RECENT_WATCH_ROW_SPACING,
    RECENT_WATCH_THUMBNAIL_HEIGHT,
)
from lumi.ui.theme.styles import apply_widget_stylesheet


class RecentWatchList(QListWidget):
    """A list that keeps action selection in the current row."""

    back_requested = Signal()

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
        self.setAutoScroll(False)
        self.setViewportMargins(*RECENT_WATCH_LIST_VIEWPORT_MARGINS)
        self.setItemDelegate(RecentWatchRowDelegate(self))
        self._row_item_height = RECENT_WATCH_THUMBNAIL_HEIGHT + 2 * LIST_ROW_VERTICAL_INSET
        self._rows: list[RecentWatchRow] = []
        self._poster_loader: PosterLoader | None = None
        self._fade_overlay = ScrollEdgeFadeOverlay(
            self.verticalScrollBar(),
            parent=self.viewport(),
        )
        self.currentRowChanged.connect(self._on_current_row_changed)

    def bind_poster_loader(self, loader: PosterLoader) -> None:
        self._poster_loader = loader
        for row in self._rows:
            row.bind_poster_loader(loader)

    def set_rows(self, rows: list[RecentWatchRowUiModel]) -> None:
        self.clear()
        self._rows = []
        for model in rows:
            item = QListWidgetItem()
            item.setSizeHint(QSize(self.viewport().width(), self._row_item_height))
            self.addItem(item)
            row = RecentWatchRow(model)
            if self._poster_loader is not None:
                row.bind_poster_loader(self._poster_loader)
            self.setItemWidget(item, row)
            self._rows.append(row)
        if rows:
            self._add_bottom_scroll_padding()
            self.setCurrentRow(0)
        self._sync_row_focus()
        self._resize_row_widgets()
        if rows:
            self._scroll_row_into_view(self.currentRow())
        self._sync_fade_overlay()

    @property
    def entry_count(self) -> int:
        return len(self._rows)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._resize_row_widgets()
        row = self.currentRow()
        if 0 <= row < len(self._rows):
            self._scroll_row_into_view(row)
        self._sync_row_focus()
        self._sync_fade_overlay()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._resize_row_widgets()
        self._sync_fade_overlay()

    def focus_playback_path(self, path: PurePosixPath) -> bool:
        for index, row in enumerate(self._rows):
            if row.model.playback_path == path:
                self.setCurrentRow(index)
                self._scroll_row_into_view(index)
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
        super().keyPressEvent(event)

    def _on_current_row_changed(self, row: int) -> None:
        self._sync_row_focus()
        if row >= 0:
            self._scroll_row_into_view(row)

    def _scroll_row_into_view(self, row: int) -> None:
        """Match library ``EntriesList`` — anchor a few rows from the top, full last row at bottom."""
        if row < 0 or row >= len(self._rows):
            return
        item = self.item(row)
        if item is None:
            return
        if row >= len(self._rows) - 1:
            self.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtBottom)
        else:
            anchor_row = max(0, row - LIST_ROWS_FROM_TOP)
            anchor_item = self.item(anchor_row)
            if anchor_item is not None:
                self.scrollToItem(anchor_item, QAbstractItemView.ScrollHint.PositionAtTop)
        item = self.item(row)
        if item is not None:
            self.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)
        self._sync_fade_overlay()

    def _add_bottom_scroll_padding(self) -> None:
        pad = QListWidgetItem()
        pad.setFlags(Qt.ItemFlag.NoItemFlags)
        pad.setSizeHint(QSize(self.viewport().width(), LIST_ROW_VERTICAL_INSET))
        self.addItem(pad)

    def _sync_fade_overlay(self) -> None:
        self._fade_overlay.sync()

    def _sync_row_focus(self) -> None:
        current_row = self.currentRow()
        has_focus = self.hasFocus()
        for index, row in enumerate(self._rows):
            selected = index == current_row
            row.set_row_selected(selected)
            row.set_action_navigation_active(has_focus and selected)
        if self._rows:
            self.viewport().update()

    def _resize_row_widgets(self) -> None:
        width = max(0, self.viewport().width())
        for index in range(self.count()):
            item = self.item(index)
            if item is None:
                continue
            if index >= len(self._rows):
                item.setSizeHint(QSize(width, LIST_ROW_VERTICAL_INSET))
                continue
            item.setSizeHint(QSize(width, self._row_item_height))
            widget = self.itemWidget(item)
            if widget is not None:
                widget.setFixedSize(width, self._row_item_height)
