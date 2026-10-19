"""Filter bar for library screen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics, QKeyEvent, QPainter, QColor
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from lumi.ui.components.icon_label import IconLabel
from lumi.ui.components.inline_tag_ribbon import InlineTagRibbon
from lumi.ui.components.keyboard_helpers import is_escape_key
from lumi.ui.icons.material_icons import IconKind
from lumi.ui.screens.library.controller import EntriesFilter
from lumi.ui.theme.colors import BLACK, TEXT_PRIMARY, TOPBAR_INACTIVE, WHITE
from lumi.ui.theme.spacing import (
    CORNER_RADIUS_SM,
    SPACE_SM,
    TOPBAR_CONTENT_INSET,
    TOPBAR_FILTER_PAD_H,
    TOPBAR_FILTER_PAD_V,
)
from lumi.ui.theme.styles import apply_widget_stylesheet
from lumi.ui.theme.typography import FONT_SIZE_TOPBAR


class _FilterButton(QWidget):
    """Filter pill — custom paint avoids native QPushButton focus chrome on macOS."""

    clicked = Signal()

    _RADIUS = CORNER_RADIUS_SM
    _PAD_V = TOPBAR_FILTER_PAD_V
    _PAD_H = TOPBAR_FILTER_PAD_H

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("filterButton")
        self._label = label
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)

    def _font(self) -> QFont:
        font = QFont()
        font.setPixelSize(FONT_SIZE_TOPBAR)
        return font

    def sizeHint(self):
        from PySide6.QtCore import QSize

        metrics = QFontMetrics(self._font())
        width = metrics.horizontalAdvance(self._label) + self._PAD_H * 2
        height = metrics.height() + self._PAD_V * 2
        return QSize(width, height)

    def paintEvent(self, event) -> None:
        del event
        rect = self.rect().adjusted(0, 0, -1, -1)
        focused = self.hasFocus()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if focused:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(WHITE))
            painter.drawRoundedRect(rect, self._RADIUS, self._RADIUS)
            painter.setPen(QColor(BLACK))
        else:
            painter.setPen(QColor(TEXT_PRIMARY))

        painter.setFont(self._font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._label)
        painter.end()

    def mousePressEvent(self, event) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.clicked.emit()
        super().mousePressEvent(event)


class TopBar(QWidget):
    filter_changed = Signal(object)
    search_changed = Signal(str)
    tag_filter_changed = Signal(object)
    recent_requested = Signal()
    rebuild_requested = Signal()
    navigate_down = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._active_filter = EntriesFilter.ALL
        self._buttons: dict[EntriesFilter, _FilterButton] = {}
        self._button_order: list[_FilterButton] = []

        self._recent_button = _FilterButton("Recent")
        self._recent_button.clicked.connect(self.recent_requested.emit)
        self._recent_button.installEventFilter(self)

        search_icon = IconLabel(IconKind.SEARCH, color=TOPBAR_INACTIVE, parent=self)
        search_icon.setObjectName("searchIcon")

        self._search = QLineEdit()
        self._search.setObjectName("searchField")
        self._search.setPlaceholderText("Search library...")
        self._search.textChanged.connect(self.search_changed.emit)
        self._search.installEventFilter(self)

        button_row = QHBoxLayout()
        button_row.setSpacing(0)
        for label, filter_value in (
            ("All", EntriesFilter.ALL),
            ("Films", EntriesFilter.FILMS),
            ("Series", EntriesFilter.SERIES),
        ):
            button = _FilterButton(label)
            button.clicked.connect(lambda f=filter_value: self._select_filter(f))
            button.installEventFilter(self)
            self._buttons[filter_value] = button
            self._button_order.append(button)
            button_row.addWidget(button)

        divider = QFrame()
        divider.setObjectName("topBarDivider")
        divider.setFrameShape(QFrame.Shape.VLine)

        self._rebuild_button = _FilterButton("Rebuild")
        self._rebuild_button.clicked.connect(self.rebuild_requested.emit)
        self._rebuild_button.installEventFilter(self)
        self._chrome_order: list[QWidget] = [
            self._recent_button,
            self._search,
            *self._button_order,
            self._rebuild_button,
        ]

        self._tag_ribbon = InlineTagRibbon(self)
        self._tag_ribbon.tag_selected.connect(self.tag_filter_changed.emit)
        self._tag_ribbon.focus_previous_requested.connect(self.focus_rebuild)
        self._tag_ribbon.focus_next_requested.connect(self.navigate_down.emit)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(0)
        controls.addWidget(self._recent_button)
        controls.addWidget(search_icon)
        controls.addWidget(self._search, stretch=1)
        controls.addLayout(button_row)
        controls.addWidget(divider)
        controls.addWidget(self._rebuild_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            TOPBAR_CONTENT_INSET,
            TOPBAR_CONTENT_INSET,
            TOPBAR_CONTENT_INSET,
            TOPBAR_CONTENT_INSET,
        )
        layout.setSpacing(SPACE_SM)
        layout.addLayout(controls)
        layout.addWidget(self._tag_ribbon)

    def clear_search(self) -> None:
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)

    def focus_search(self) -> None:
        self._search.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def search_has_focus(self) -> bool:
        focus = QApplication.focusWidget()
        return focus is not None and (focus is self._search or self._search.isAncestorOf(focus))

    def append_search_character(self, char: str) -> None:
        self._search.end(False)
        self._search.insert(char)

    def remove_last_search_character(self) -> None:
        if not self._search.text():
            return
        self._search.end(False)
        self._search.backspace()

    def set_active_filter(self, filter_value: EntriesFilter) -> None:
        self._active_filter = filter_value

    def set_tags(self, tags: list[str]) -> None:
        self._tag_ribbon.set_tags(tags)

    def set_active_tag(self, tag: str | None) -> None:
        self._tag_ribbon.set_active_tag(tag)

    def focus_first_filter(self) -> None:
        if self._button_order:
            self._button_order[0].setFocus(Qt.FocusReason.OtherFocusReason)

    def focus_rebuild(self) -> None:
        self._rebuild_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def focus_tags_or_entries(self) -> None:
        if self._tag_ribbon.has_tags():
            self._tag_ribbon.focus_first_tag()
            return
        self.navigate_down.emit()

    def focus_tags_or_first_filter(self) -> None:
        if self._tag_ribbon.has_tags():
            self._tag_ribbon.focus_first_tag()
            return
        self.focus_first_filter()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._search:
            if event.type() != QEvent.Type.KeyPress:
                return super().eventFilter(watched, event)
            key_event = event
            if not isinstance(key_event, QKeyEvent):
                return super().eventFilter(watched, event)
            if key_event.key() == Qt.Key.Key_Down:
                self.focus_tags_or_entries()
                return True
            if key_event.key() == Qt.Key.Key_Left and self._search.cursorPosition() == 0:
                self._recent_button.setFocus(Qt.FocusReason.TabFocusReason)
                return True
            if (
                key_event.key() == Qt.Key.Key_Right
                and self._search.cursorPosition() == len(self._search.text())
            ):
                self._buttons[EntriesFilter.ALL].setFocus(Qt.FocusReason.TabFocusReason)
                return True
            if is_escape_key(key_event.key()):
                if self._search.text():
                    self._search.clear()
                return True
            return super().eventFilter(watched, event)

        if not isinstance(watched, _FilterButton) or watched not in self._chrome_order:
            return super().eventFilter(watched, event)

        if event.type() == QEvent.Type.FocusIn:
            watched.update()
            return False

        if event.type() == QEvent.Type.FocusOut:
            watched.update()
            return False

        if event.type() != QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)

        key_event = event
        if not isinstance(key_event, QKeyEvent):
            return super().eventFilter(watched, event)

        key = key_event.key()
        index = self._chrome_order.index(watched)

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            watched.clicked.emit()
            return True
        if key == Qt.Key.Key_Down:
            self.focus_tags_or_entries()
            return True
        if key == Qt.Key.Key_Up:
            return True
        if key == Qt.Key.Key_Right:
            if index < len(self._chrome_order) - 1:
                self._chrome_order[index + 1].setFocus(Qt.FocusReason.TabFocusReason)
            return True
        if key == Qt.Key.Key_Left:
            if index > 0:
                self._chrome_order[index - 1].setFocus(Qt.FocusReason.TabFocusReason)
            return True

        return super().eventFilter(watched, event)

    def _select_filter(self, filter_value: EntriesFilter) -> None:
        self._active_filter = filter_value
        self.filter_changed.emit(filter_value)
