"""Static title for the Recently Watched destination."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from lumi.ui.theme.spacing import LIST_ROW_LEFT_INSET
from lumi.ui.theme.styles import apply_widget_stylesheet


class RecentWatchHeader(QWidget):
    """Non-interactive recent page title (prototype chrome-recent)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RecentWatchHeader")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._title = QLabel("Recently watched")
        self._title.setObjectName("recentPageTitle")
        self._title.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        from PySide6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(self)
        layout.setContentsMargins(LIST_ROW_LEFT_INSET, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._title)
