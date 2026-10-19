"""Activatable chrome for the Recently Watched destination."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QFontMetrics, QKeyEvent, QMouseEvent, QPainter, QPen, QColor
from PySide6.QtWidgets import QVBoxLayout, QWidget

from lumi.ui.components.keyboard_helpers import is_escape_key
from lumi.ui.theme.colors import TEXT_PRIMARY, WHITE
from lumi.ui.theme.spacing import CORNER_RADIUS_SM, FOCUS_RING_WIDTH, LIST_ROW_LEFT_INSET
from lumi.ui.theme.styles import apply_widget_stylesheet
from lumi.ui.theme.typography import FONT_SIZE_TOPBAR


class RecentWatchHeader(QWidget):
    """Prototype-style recent page title with kb-focus ring."""

    activated = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RecentWatchHeader")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self._title = "Recently watched"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(LIST_ROW_LEFT_INSET, 0, 0, 0)
        layout.addStretch(1)

    def sizeHint(self) -> QSize:
        font = self._title_font()
        metrics = QFontMetrics(font)
        ring = FOCUS_RING_WIDTH * 2
        return QSize(metrics.horizontalAdvance(self._title) + ring, metrics.height() + 12 + ring)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def _title_font(self) -> QFont:
        font = QFont()
        font.setPixelSize(FONT_SIZE_TOPBAR)
        font.setWeight(QFont.Weight.Medium)
        return font

    def paintEvent(self, event) -> None:
        del event
        font = self._title_font()
        metrics = QFontMetrics(font)
        text_h = metrics.height()
        ring = FOCUS_RING_WIDTH
        outer = self.rect()
        text_rect = outer.adjusted(
            LIST_ROW_LEFT_INSET + ring,
            6 + ring,
            -ring,
            -ring,
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(font)
        painter.setPen(QColor(TEXT_PRIMARY))
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._title,
        )
        if self.hasFocus():
            outline = outer.adjusted(
                LIST_ROW_LEFT_INSET + ring // 2,
                6 + ring // 2,
                -(ring + 1) // 2,
                -(ring + 1) // 2,
            )
            pen = QPen(QColor(WHITE), ring)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(outline, CORNER_RADIUS_SM, CORNER_RADIUS_SM)
        painter.end()

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

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.update()
