"""Filter bar for library screen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QRect, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from lumi.ui.components.icon_label import IconLabel
from lumi.ui.components.inline_tag_ribbon import InlineTagRibbon
from lumi.ui.components.keyboard_helpers import is_escape_key
from lumi.ui.icons.material_icons import IconKind, paint_icon
from lumi.ui.screens.library.controller import EntriesFilter
from lumi.ui.theme.colors import (
    ALPHABET_ACTIVE_TINT,
    TOPBAR_ACTIVE,
    TOPBAR_FOCUS_TINT,
    TOPBAR_INACTIVE,
    TOPBAR_SURFACE,
    WHITE,
)
from lumi.ui.theme.spacing import (
    FOCUS_RING_WIDTH,
    ICON_SIZE,
    TOPBAR_CHROME_GAP,
    TOPBAR_CONTENT_MARGINS,
    TOPBAR_DIVIDER_MARGIN_H,
    TOPBAR_FILTER_GAP,
    TOPBAR_HIT_TARGET,
    TOPBAR_ICON_RADIUS,
    TOPBAR_SEARCH_ICON_SIZE,
    TOPBAR_SEARCH_INNER_GAP,
    TOPBAR_SEARCH_PADDING_H,
    TOPBAR_SEARCH_PADDING_V,
    TOPBAR_SECTION_GAP,
)
from lumi.ui.theme.styles import apply_widget_stylesheet


def _paint_kb_focus_ring(painter: QPainter, outer: QRect, radius: float) -> None:
    ring = FOCUS_RING_WIDTH
    outline = outer.adjusted(ring // 2, ring // 2, -(ring + 1) // 2, -(ring + 1) // 2)
    pen = QPen(QColor(WHITE), ring)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(outline, radius + ring // 2, radius + ring // 2)


class _ChromeIconButton(QWidget):
    """Prototype-style icon control with explicit keyboard focus rendering."""

    clicked = Signal()

    def __init__(self, icon: IconKind, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chromeIconButton")
        self._icon = icon
        self._selected = False
        self.setToolTip(label)
        self.setAccessibleName(label)
        self.setFixedSize(TOPBAR_HIT_TARGET, TOPBAR_HIT_TARGET)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)

    def set_selected(self, selected: bool) -> None:
        if selected == self._selected:
            return
        self._selected = selected
        self.update()

    def paintEvent(self, event) -> None:
        del event
        outer = self.rect().adjusted(0, 0, -1, -1)
        radius = TOPBAR_ICON_RADIUS
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(ALPHABET_ACTIVE_TINT))
            painter.drawRoundedRect(outer, radius, radius)
            icon_color = TOPBAR_ACTIVE
        elif self.hasFocus():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(TOPBAR_FOCUS_TINT))
            painter.drawRoundedRect(outer, radius, radius)
            icon_color = WHITE
        else:
            icon_color = TOPBAR_INACTIVE

        if self.hasFocus():
            _paint_kb_focus_ring(painter, self.rect(), radius)

        icon_rect = outer.adjusted(
            (outer.width() - ICON_SIZE) // 2,
            (outer.height() - ICON_SIZE) // 2,
            -((outer.width() - ICON_SIZE + 1) // 2),
            -((outer.height() - ICON_SIZE + 1) // 2),
        )
        paint_icon(painter, icon_rect, self._icon, QColor(icon_color))
        painter.end()

    def mousePressEvent(self, event) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.clicked.emit()
        super().mousePressEvent(event)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.update()


class _SearchPill(QWidget):
    """Search field container with prototype kb-focus ring."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("searchPill")
        self._search_focused = False

    def set_search_focused(self, focused: bool) -> None:
        if focused == self._search_focused:
            return
        self._search_focused = focused
        self.update()

    def paintEvent(self, event) -> None:
        del event
        outer = self.rect().adjusted(0, 0, -1, -1)
        radius = outer.height() // 2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(TOPBAR_SURFACE))
        painter.drawRoundedRect(outer, radius, radius)
        if self._search_focused:
            _paint_kb_focus_ring(painter, self.rect(), radius)
        painter.end()


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
        self._buttons: dict[EntriesFilter, _ChromeIconButton] = {}
        self._button_order: list[_ChromeIconButton] = []

        self._recent_button = _ChromeIconButton(IconKind.HISTORY, "Recently watched")
        self._recent_button.clicked.connect(self.recent_requested.emit)

        self._search_pill = _SearchPill(self)
        self._search_pill.setFixedHeight(TOPBAR_HIT_TARGET)
        self._search_pill.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        search_layout = QHBoxLayout(self._search_pill)
        search_layout.setContentsMargins(
            TOPBAR_SEARCH_PADDING_H,
            TOPBAR_SEARCH_PADDING_V,
            TOPBAR_SEARCH_PADDING_H,
            TOPBAR_SEARCH_PADDING_V,
        )
        search_layout.setSpacing(TOPBAR_SEARCH_INNER_GAP)

        search_icon = IconLabel(
            IconKind.SEARCH,
            color=TOPBAR_INACTIVE,
            size=TOPBAR_SEARCH_ICON_SIZE,
            parent=self._search_pill,
        )
        search_icon.setObjectName("searchIcon")

        self._search = QLineEdit(self._search_pill)
        self._search.setObjectName("searchField")
        self._search.setPlaceholderText("Search library…")
        self._search.textChanged.connect(self.search_changed.emit)
        self._search.installEventFilter(self)
        search_layout.addWidget(search_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        search_layout.addWidget(self._search, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

        filter_host = QWidget()
        filter_host.setObjectName("filterIcons")
        filter_layout = QHBoxLayout(filter_host)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(TOPBAR_FILTER_GAP)
        for icon, label, filter_value in (
            (IconKind.GRID_VIEW, "All titles", EntriesFilter.ALL),
            (IconKind.PLAY_CIRCLE, "Films", EntriesFilter.FILMS),
            (IconKind.SERIES, "Series", EntriesFilter.SERIES),
        ):
            button = _ChromeIconButton(icon, label)
            button.clicked.connect(lambda f=filter_value: self._select_filter(f))
            self._buttons[filter_value] = button
            self._button_order.append(button)
            filter_layout.addWidget(button)

        divider = QFrame()
        divider.setObjectName("topBarDivider")
        divider.setFrameShape(QFrame.Shape.VLine)
        divider_host = QWidget()
        divider_host.setObjectName("topBarDividerHost")
        divider_layout = QHBoxLayout(divider_host)
        divider_layout.setContentsMargins(TOPBAR_DIVIDER_MARGIN_H, 0, TOPBAR_DIVIDER_MARGIN_H, 0)
        divider_layout.setSpacing(0)
        divider_layout.addWidget(divider, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._rebuild_button = _ChromeIconButton(IconKind.REFRESH, "Rebuild library")
        self._rebuild_button.clicked.connect(self.rebuild_requested.emit)
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
        controls.setSpacing(TOPBAR_CHROME_GAP)
        controls.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        controls.addWidget(self._recent_button)
        controls.addWidget(self._search_pill, stretch=1)
        controls.addWidget(filter_host)
        controls.addWidget(divider_host)
        controls.addWidget(self._rebuild_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*TOPBAR_CONTENT_MARGINS)
        layout.setSpacing(TOPBAR_SECTION_GAP)
        layout.addLayout(controls)
        layout.addWidget(self._tag_ribbon)

        for chrome_widget in self._chrome_order:
            if isinstance(chrome_widget, _ChromeIconButton):
                chrome_widget.installEventFilter(self)

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
        for value, button in self._buttons.items():
            button.set_selected(value is filter_value)

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
            if event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
                self._search_pill.set_search_focused(self._search.hasFocus())
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
                else:
                    self.navigate_down.emit()
                return True
            return super().eventFilter(watched, event)

        if not isinstance(watched, _ChromeIconButton) or watched not in self._chrome_order:
            return super().eventFilter(watched, event)

        if event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
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
        self.set_active_filter(filter_value)
        self.filter_changed.emit(filter_value)
