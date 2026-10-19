"""Inline, keyboard-navigable tag filter ribbon."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QRect, Signal, QSize
from PySide6.QtGui import QFont, QFontMetrics, QKeyEvent, QPainter, QPen, QColor
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from lumi.ui.theme.colors import (
    ALPHABET_ACTIVE_TINT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TOPBAR_ACTIVE,
    TOPBAR_FOCUS_TINT,
    TOPBAR_SURFACE,
    WHITE,
)
from lumi.ui.theme.spacing import (
    FOCUS_RING_WIDTH,
    TAG_CHIP_GAP,
    TAG_CHIP_PADDING_H,
    TAG_CHIP_PADDING_V,
)
from lumi.ui.theme.styles import apply_widget_stylesheet
from lumi.ui.theme.text_metrics import ink_single_line_height, ink_text_width
from lumi.ui.theme.typography import FONT_SIZE_TAG


class _TagRibbonButton(QWidget):
    """Pill tag control — QSS border-radius alone is unreliable on macOS."""

    clicked = Signal()

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tagRibbonButton")
        self._label = label
        self._selected = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def text(self) -> str:
        return self._label

    def set_selected(self, selected: bool) -> None:
        if selected == self._selected:
            return
        self._selected = selected
        self.update()

    def _font(self) -> QFont:
        font = QFont()
        font.setPixelSize(FONT_SIZE_TAG)
        return font

    def sizeHint(self) -> QSize:
        metrics = QFontMetrics(self._font())
        width = TAG_CHIP_PADDING_H * 2 + ink_text_width(metrics, self._label)
        height = TAG_CHIP_PADDING_V * 2 + ink_single_line_height(metrics, self._label)
        ring = FOCUS_RING_WIDTH * 2
        return QSize(width + ring, height + ring)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        del event
        metrics = QFontMetrics(self._font())
        inner_h = TAG_CHIP_PADDING_V * 2 + ink_single_line_height(metrics, self._label)
        inner_w = TAG_CHIP_PADDING_H * 2 + ink_text_width(metrics, self._label)
        ring = FOCUS_RING_WIDTH
        outer = self.rect()
        content = outer.adjusted(ring, ring, -ring, -ring)
        pill_x = content.x() + max(0, (content.width() - inner_w) // 2)
        pill_y = content.y() + max(0, (content.height() - inner_h) // 2)
        pill_rect = QRect(pill_x, pill_y, min(inner_w, content.width()), min(inner_h, content.height()))
        radius = pill_rect.height() / 2

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._selected:
            painter.setBrush(QColor(ALPHABET_ACTIVE_TINT))
            painter.setPen(Qt.PenStyle.NoPen)
            text_color = TOPBAR_ACTIVE
        elif self.hasFocus():
            painter.setBrush(QColor(TOPBAR_FOCUS_TINT))
            painter.setPen(Qt.PenStyle.NoPen)
            text_color = TEXT_PRIMARY
        else:
            painter.setBrush(QColor(TOPBAR_SURFACE))
            painter.setPen(Qt.PenStyle.NoPen)
            text_color = TEXT_MUTED

        painter.drawRoundedRect(pill_rect, radius, radius)

        if self.hasFocus():
            outline = outer.adjusted(ring // 2, ring // 2, -(ring + 1) // 2, -(ring + 1) // 2)
            pen = QPen(QColor(WHITE), ring)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(outline, radius + ring // 2, radius + ring // 2)

        painter.setFont(self._font())
        painter.setPen(QColor(text_color))
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, self._label)
        painter.end()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.update()


class InlineTagRibbon(QWidget):
    """Horizontal tag selector that delegates focus moves at its boundaries."""

    tag_selected = Signal(object)
    focus_previous_requested = Signal()
    focus_next_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("InlineTagRibbon")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._tags: list[str] = []
        self._active_tag: str | None = None
        self._buttons: list[_TagRibbonButton] = []
        self._button_tags: dict[_TagRibbonButton, str | None] = {}

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(TAG_CHIP_GAP)
        self.hide()

    def set_tags(self, tags: list[str]) -> None:
        """Show the supplied tags, preserving their established display order."""
        if tags == self._tags:
            return

        self._tags = list(tags)
        self._clear_buttons()
        if not self._tags:
            self.hide()
            return

        self._insert_button("All tags", None)
        for tag in self._tags:
            self._insert_button(tag[:1].upper() + tag[1:], tag)
        self._layout.addStretch(1)
        self.show()
        self._sync_selected_button()

    def set_active_tag(self, tag: str | None) -> None:
        """Reflect a tag selection made elsewhere in the library chrome."""
        self._active_tag = tag
        self._sync_selected_button()

    def has_tags(self) -> bool:
        return bool(self._buttons)

    def focus_first_tag(self) -> None:
        if self._buttons:
            self._buttons[0].setFocus(Qt.FocusReason.OtherFocusReason)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if not isinstance(watched, _TagRibbonButton) or watched not in self._buttons:
            return super().eventFilter(watched, event)
        if event.type() != QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)

        key_event = event
        if not isinstance(key_event, QKeyEvent):
            return super().eventFilter(watched, event)

        index = self._buttons.index(watched)
        key = key_event.key()
        if key == Qt.Key.Key_Left:
            if index == 0:
                self.focus_previous_requested.emit()
            else:
                self._buttons[index - 1].setFocus(Qt.FocusReason.TabFocusReason)
            return True
        if key == Qt.Key.Key_Right:
            if index == len(self._buttons) - 1:
                self.focus_next_requested.emit()
            else:
                self._buttons[index + 1].setFocus(Qt.FocusReason.TabFocusReason)
            return True
        if key == Qt.Key.Key_Up:
            self.focus_previous_requested.emit()
            return True
        if key == Qt.Key.Key_Down:
            self.focus_next_requested.emit()
            return True
        return super().eventFilter(watched, event)

    def _clear_buttons(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.removeEventFilter(self)
                widget.deleteLater()
        self._buttons.clear()
        self._button_tags.clear()

    def _insert_button(self, label: str, tag: str | None) -> None:
        button = _TagRibbonButton(label)
        button.clicked.connect(lambda value=tag: self._select_tag(value))
        button.installEventFilter(self)
        self._layout.addWidget(button)
        self._buttons.append(button)
        self._button_tags[button] = tag

    def _select_tag(self, tag: str | None) -> None:
        self._active_tag = tag
        self._sync_selected_button()
        self.tag_selected.emit(tag)

    def _sync_selected_button(self) -> None:
        for button in self._buttons:
            button.set_selected(self._button_tags[button] == self._active_tag)
