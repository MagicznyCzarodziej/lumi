"""Activatable chrome for the Recently Watched destination."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from lumi.ui.components.keyboard_helpers import is_escape_key
from lumi.ui.theme.styles import apply_widget_stylesheet


class RecentWatchHeader(QWidget):
    """A title-only header; activation returns to the library."""

    activated = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RecentWatchHeader")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)

        title = QLabel("Recently watched")
        title.setObjectName("title")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(title)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if is_escape_key(event.key()) or event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            self.activated.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)
