"""Small painted icon label widget."""

from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from lumi.ui.icons.material_icons import IconKind, paint_icon
from lumi.ui.theme.spacing import ICON_SIZE


class IconLabel(QLabel):
    def __init__(self, kind: IconKind, *, color: str, size: int = ICON_SIZE, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind = kind
        self._icon_color = color
        self._icon_size = size
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        icon_left = (self.width() - self._icon_size) // 2
        icon_top = (self.height() - self._icon_size) // 2
        icon_rect = QRect(icon_left, icon_top, self._icon_size, self._icon_size)
        paint_icon(painter, icon_rect, self._kind, QColor(self._icon_color))
        painter.end()
