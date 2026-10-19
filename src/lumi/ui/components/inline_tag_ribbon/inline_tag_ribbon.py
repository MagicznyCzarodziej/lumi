"""Inline, keyboard-navigable tag filter ribbon."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget

from lumi.ui.theme.spacing import TAG_CHIP_GAP
from lumi.ui.theme.styles import apply_widget_stylesheet


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
        self._buttons: list[QPushButton] = []
        self._button_tags: dict[QPushButton, str | None] = {}

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

        self._insert_button("All", None)
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
        if not isinstance(watched, QPushButton) or watched not in self._buttons:
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
        button = QPushButton(label)
        button.setObjectName("tagRibbonButton")
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        button.clicked.connect(lambda checked=False, value=tag: self._select_tag(value))
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
            button.setProperty("selected", self._button_tags[button] == self._active_tag)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
