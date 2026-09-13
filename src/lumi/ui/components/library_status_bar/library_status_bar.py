"""Full-width bottom strip for long-running library operations."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from lumi.ui.theme.spacing import SPACE_SM
from lumi.ui.theme.styles import apply_widget_stylesheet
from lumi.ui.theme.typography import SIDEBAR_MENU_FONT_SIZE


class LibraryStatusBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LibraryStatusBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setFixedHeight(SPACE_SM * 2 + SIDEBAR_MENU_FONT_SIZE + 2)

        self._label = QLabel()
        self._label.setObjectName("statusText")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._label, stretch=1)

        self.hide()

    def set_progress(self, progress: tuple[int, int, str] | None) -> None:
        if progress is None:
            self.hide()
            return
        completed, total, directory_name = progress
        if directory_name:
            text = f"Building library… {completed}/{total} — {directory_name}"
        else:
            text = f"Building library… {completed}/{total}"
        self._label.setText(text)
        self.show()
        parent = self.parentWidget()
        if parent is not None and hasattr(parent, "position_status_bar"):
            parent.position_status_bar()
