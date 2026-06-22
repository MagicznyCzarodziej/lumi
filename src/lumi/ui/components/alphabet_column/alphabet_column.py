"""A–Z index column for library screen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from lumi.ui.components.keyboard_helpers import letter_key
from lumi.ui.components.scroll_edge_fades import paint_scroll_edge_fades
from lumi.ui.theme.colors import BACKGROUND, BLACK, TEXT_PRIMARY, WHITE
from lumi.ui.theme.spacing import (
    ALPHABET_COLUMN_HEIGHT,
    ALPHABET_COLUMN_WIDTH,
    ALPHABET_FADE_HEIGHT,
    ALPHABET_LETTER_SIZE,
    CORNER_RADIUS_SM,
)
from lumi.ui.theme.styles import apply_widget_stylesheet
from lumi.ui.theme.typography import FONT_SIZE_ALPHABET

_COLUMN_WIDTH = ALPHABET_COLUMN_WIDTH
_COLUMN_HEIGHT = ALPHABET_COLUMN_HEIGHT
_LETTER_SIZE = ALPHABET_LETTER_SIZE
_LETTER_ROW_HEIGHT = _LETTER_SIZE
_FADE_HEIGHT = ALPHABET_FADE_HEIGHT
_CORNER_RADIUS = CORNER_RADIUS_SM


class _AlphabetFadeOverlay(QWidget):
    def __init__(self, column: "AlphabetColumn") -> None:
        super().__init__(column)
        self._column = column
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def paintEvent(self, event) -> None:
        del event
        self._column._paint_edge_fades(self)


class AlphabetColumn(QWidget):
    """Custom letter column with centered scrolling."""

    letter_activated = Signal(str)
    exit_to_entries = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AlphabetColumn")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(_COLUMN_WIDTH, _COLUMN_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)

        self._symbols: list[str] = []
        self._focused_index = 0
        self._active_letter: str | None = None
        self._scroll_y = 0

        self._fade_overlay = _AlphabetFadeOverlay(self)
        self._sync_fade_overlay()

    def count(self) -> int:
        return len(self._symbols)

    def currentRow(self) -> int:
        return self._focused_index

    def set_symbols(self, symbols: list[str]) -> None:
        if symbols == self._symbols:
            return
        focused_letter: str | None = None
        if self._symbols and 0 <= self._focused_index < len(self._symbols):
            focused_letter = self._symbols[self._focused_index]
        self._symbols = list(symbols)
        if focused_letter is not None and focused_letter in self._symbols:
            self._focused_index = self._symbols.index(focused_letter)
            self._scroll_y = self.scroll_offset_for_index(self._focused_index)
        else:
            self._focused_index = 0
            self._scroll_y = 0
        self._sync_fade_overlay()
        self.update()

    def set_active_letter(self, letter: str | None) -> None:
        self._active_letter = letter
        self.update()

    def index_for_letter(self, letter: str | None) -> int:
        return self._index_for_letter(letter)

    def scroll_to_letter(self, letter: str | None) -> None:
        """Passive sync while browsing entries — never interrupts alphabet keyboard nav."""
        if self._keyboard_focused():
            return
        index = self._index_for_letter(letter)
        if index < 0:
            return
        self._scroll_y = self.scroll_offset_for_index(index)
        self._sync_fade_overlay()
        self.update()

    def scroll_to_row(self, row: int) -> None:
        if row < 0 or row >= len(self._symbols):
            return
        self._focused_index = row
        self._scroll_y = self.scroll_offset_for_index(row)
        self._sync_fade_overlay()
        self.update()

    def scroll_offset_for_index(self, index: int) -> int:
        if index < 0:
            return 0
        content_height = len(self._symbols) * _LETTER_ROW_HEIGHT
        viewport_height = self.height()
        if content_height <= viewport_height:
            return 0
        item_center = index * _LETTER_ROW_HEIGHT + _LETTER_ROW_HEIGHT // 2
        centered = item_center - viewport_height // 2
        max_scroll = content_height - viewport_height
        return max(0, min(centered, max_scroll))

    def _index_for_letter(self, letter: str | None) -> int:
        if letter is None:
            return -1
        try:
            return self._symbols.index(letter)
        except ValueError:
            return -1

    def _keyboard_focused(self) -> bool:
        focus = QApplication.focusWidget()
        return focus is not None and (focus is self or self.isAncestorOf(focus))

    def _move_focus(self, delta: int) -> None:
        if not self._symbols:
            return
        next_index = max(0, min(self._focused_index + delta, len(self._symbols) - 1))
        if next_index == self._focused_index:
            return
        self._focused_index = next_index
        self._scroll_y = self.scroll_offset_for_index(next_index)
        self._sync_fade_overlay()
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Right:
            self.exit_to_entries.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Left:
            event.accept()
            return
        if event.key() == Qt.Key.Key_Up:
            self._move_focus(-1)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Down:
            self._move_focus(1)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space:
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if 0 <= self._focused_index < len(self._symbols):
                self.letter_activated.emit(self._symbols[self._focused_index])
            event.accept()
            return
        letter = letter_key(event)
        if letter is not None:
            self._jump_to_letter(letter)
            event.accept()
            return
        super().keyPressEvent(event)

    def _jump_to_letter(self, letter: str) -> None:
        index = self._index_for_letter(letter)
        if index < 0:
            return
        self._focused_index = index
        self._scroll_y = self.scroll_offset_for_index(index)
        self._sync_fade_overlay()
        self.update()

    def mousePressEvent(self, event) -> None:
        index = self._index_at_y(event.position().y() + self._scroll_y)
        if index >= 0:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self._focused_index = index
            self._scroll_y = self.scroll_offset_for_index(index)
            self._sync_fade_overlay()
            self.update()
            self.letter_activated.emit(self._symbols[index])
        super().mousePressEvent(event)

    def _index_at_y(self, y: float) -> int:
        if not self._symbols:
            return -1
        index = int(y // _LETTER_ROW_HEIGHT)
        if 0 <= index < len(self._symbols):
            return index
        return -1

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(BACKGROUND))
        painter.translate(0, -self._scroll_y)

        letter_font = QFont()
        letter_font.setPixelSize(FONT_SIZE_ALPHABET)
        painter.setFont(letter_font)

        for index, symbol in enumerate(self._symbols):
            rect = QRect(0, index * _LETTER_ROW_HEIGHT, _LETTER_SIZE, _LETTER_SIZE)
            focused = self._keyboard_focused() and index == self._focused_index
            active = symbol == self._active_letter

            if focused:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(WHITE))
                painter.drawRoundedRect(rect, _CORNER_RADIUS, _CORNER_RADIUS)
                painter.setPen(QColor(BLACK))
            elif active:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255, 77))
                painter.drawRoundedRect(rect, _CORNER_RADIUS, _CORNER_RADIUS)
                painter.setPen(QColor(TEXT_PRIMARY))
            else:
                painter.setPen(QColor(255, 255, 255, 128))

            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, symbol)

        painter.end()

    def _sync_fade_overlay(self) -> None:
        self._fade_overlay.setGeometry(0, 0, self.width(), self.height())
        self._fade_overlay.raise_()
        self._fade_overlay.update()

    def _should_fade(self) -> bool:
        content_height = len(self._symbols) * _LETTER_ROW_HEIGHT
        return content_height > self.height()

    def _paint_edge_fades(self, target: QWidget) -> None:
        if not self._should_fade():
            return
        paint_scroll_edge_fades(
            target,
            scroll_value=self._scroll_y,
            scroll_max=self.scroll_offset_for_index(len(self._symbols) - 1),
            fade_height=_FADE_HEIGHT,
            background=QColor(BACKGROUND),
        )
