"""Animated skeleton shimmer overlay for loading placeholders."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

from lumi.ui.theme.colors import BACKGROUND, SKELETON_SHIMMER
from lumi.ui.theme.spacing import SPACE_MD


class SkeletonOverlay(QWidget):
    def __init__(self, *, compact: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._compact = compact
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._advance)
        self.hide()

    def start(self) -> None:
        self._phase = 0
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _advance(self) -> None:
        self._phase = (self._phase + 4) % (self.width() + 120 or 120)
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(BACKGROUND))

        width = max(self.width(), 1)
        gradient = QLinearGradient(self._phase - 120, 0, self._phase + 120, 0)
        gradient.setColorAt(0.0, QColor(BACKGROUND))
        gradient.setColorAt(0.45, QColor(SKELETON_SHIMMER))
        gradient.setColorAt(0.55, QColor(SKELETON_SHIMMER))
        gradient.setColorAt(1.0, QColor(BACKGROUND))
        painter.fillRect(0, 0, width, self.height(), gradient)

        block_color = QColor(SKELETON_SHIMMER)
        margin = 0 if self._compact else 16
        if self._compact:
            painter.fillRect(SPACE_MD, 16, min(250, width - SPACE_MD), 18, block_color)
            painter.fillRect(SPACE_MD, 42, min(400, width - SPACE_MD), 28, block_color)
        else:
            block_height = max(12, (self.height() - margin * 3) // 4)
            y = margin
            for index in range(4):
                block_width = int(width * (0.92 - index * 0.08))
                painter.fillRect(margin, y, block_width, block_height, block_color)
                y += block_height + margin
        painter.end()
