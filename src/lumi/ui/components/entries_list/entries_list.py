"""Scrollable entries list."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QElapsedTimer, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem, QWidget

from lumi.ui.components.keyboard_helpers import is_escape_key, search_character
from lumi.ui.components.list_entry import ListEntryUiModel, NameDisplayStrategy
from lumi.ui.components.list_entry_delegate import ListEntryDelegate
from lumi.ui.components.scroll_edge_fades import ScrollEdgeFadeOverlay
from lumi.ui.theme.spacing import (
    LIST_ROW_MARGINS,
    LIST_ROWS_FROM_TOP,
    LIST_VIEWPORT_MARGINS,
)
from lumi.ui.theme.styles import apply_widget_stylesheet

_ROWS_FROM_TOP = LIST_ROWS_FROM_TOP
_REPEAT_NAV_INTERVAL_MS = 50


class EntriesList(QListWidget):
    entry_activated = Signal(int)
    focus_left_requested = Signal()
    focus_right_requested = Signal()
    focus_up_requested = Signal()
    type_to_search = Signal(str)
    clear_search_requested = Signal()
    backspace_search_requested = Signal()
    back_requested = Signal()

    def __init__(
        self,
        *,
        name_display_strategy: NameDisplayStrategy = NameDisplayStrategy.REGULAR,
        escape_clears_search: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._escape_clears_search = escape_clears_search
        self.setObjectName("EntriesList")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setItemDelegate(
            ListEntryDelegate(
                name_display_strategy=name_display_strategy,
                content_margins=LIST_ROW_MARGINS,
                parent=self,
            )
        )
        self.setSpacing(0)
        self.setUniformItemSizes(False)
        self.setViewportMargins(*LIST_VIEWPORT_MARGINS)
        self.setAutoScroll(False)
        self._models: list[ListEntryUiModel] = []
        self._focused_row = 0
        self._fade_overlay = ScrollEdgeFadeOverlay(
            self.verticalScrollBar(),
            parent=self.viewport(),
        )
        self._repeat_nav_clock = QElapsedTimer()
        self._repeat_nav_clock.start()
        self._defer_poster_update = False
        self.currentRowChanged.connect(self._on_row_changed)
        self.itemActivated.connect(self._on_item_activated)

    def set_entries(self, entries: list[ListEntryUiModel], *, preserve_focus: bool = False) -> None:
        focus_key: str | None = None
        previous_row = self._focused_row
        if preserve_focus and self._models and 0 <= self._focused_row < len(self._models):
            focus_key = _entry_focus_key(self._models[self._focused_row])

        self._models = entries
        self._defer_poster_update = False
        self.clear()
        for model in entries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, model)
            self.addItem(item)
        if entries:
            row = 0
            if focus_key is not None:
                for index, model in enumerate(entries):
                    if _entry_focus_key(model) == focus_key:
                        row = index
                        break
                else:
                    row = min(previous_row, len(entries) - 1)
            self.setCurrentRow(row)
            self._focused_row = row
        else:
            self._focused_row = 0
        self._sync_fade_overlay()

    def focused_row(self) -> int:
        return self._focused_row

    def consume_defer_poster_update(self) -> bool:
        """True when the latest row change came from held-key auto-repeat."""
        defer = self._defer_poster_update
        self._defer_poster_update = False
        return defer

    def scroll_to_row(self, row: int) -> None:
        if row < 0 or row >= self.count():
            return
        self._defer_poster_update = False
        if self.currentRow() == row:
            self._scroll_to_row_offset(row)
        else:
            self.setCurrentRow(row)
        self._focused_row = row
        self._sync_fade_overlay()

    def _scroll_to_row_offset(self, row: int) -> None:
        """Keep the focused row a few items below the top of the viewport."""
        anchor_row = max(0, row - _ROWS_FROM_TOP)
        anchor_item = self.item(anchor_row)
        if anchor_item is not None:
            self.scrollToItem(anchor_item, QAbstractItemView.ScrollHint.PositionAtTop)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_fade_overlay()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_fade_overlay()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        char = search_character(event)
        if char is not None:
            self.type_to_search.emit(char)
            event.accept()
            return
        if is_escape_key(event.key()):
            if self._escape_clears_search:
                self.clear_search_requested.emit()
            else:
                self.back_requested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Backspace:
            if self._escape_clears_search:
                self.backspace_search_requested.emit()
            else:
                self.back_requested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Left:
            self.focus_left_requested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Right:
            self.focus_right_requested.emit()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            if event.isAutoRepeat() and self._repeat_nav_clock.elapsed() < _REPEAT_NAV_INTERVAL_MS:
                event.accept()
                return
            if event.isAutoRepeat():
                self._repeat_nav_clock.restart()
                self._defer_poster_update = True
            else:
                self._defer_poster_update = False
            if event.key() == Qt.Key.Key_Up:
                if self.currentRow() <= 0:
                    self.focus_up_requested.emit()
                else:
                    super().keyPressEvent(event)
            else:
                super().keyPressEvent(event)
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            row = self.currentRow()
            item = self.item(row) if row >= 0 else None
            if item is not None:
                self._on_item_activated(item)
            event.accept()
            return
        super().keyPressEvent(event)

    def _sync_fade_overlay(self) -> None:
        self._fade_overlay.sync()

    def _on_row_changed(self, row: int) -> None:
        if row < 0:
            return
        self._focused_row = row
        self._scroll_to_row_offset(row)
        self._sync_fade_overlay()

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        row = self.row(item)
        if 0 <= row < len(self._models):
            self._models[row].on_click()
            self.entry_activated.emit(row)


def _entry_focus_key(model: ListEntryUiModel) -> str:
    return model.name.sort_name or model.name.name
