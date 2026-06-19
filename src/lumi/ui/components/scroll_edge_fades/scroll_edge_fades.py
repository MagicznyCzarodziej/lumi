"""Top/bottom edge fades for scrollable lists — matches alphabet column."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPaintEvent
from PySide6.QtWidgets import QScrollBar, QWidget

from lumi.ui.theme.colors import BACKGROUND
from lumi.ui.theme.spacing import ALPHABET_FADE_HEIGHT


def paint_scroll_edge_fades(
    target: QWidget,
    *,
    scroll_value: int,
    scroll_max: int,
    fade_height: int = ALPHABET_FADE_HEIGHT,
    background: QColor | None = None,
) -> None:
    if scroll_max <= 0:
        return

    width = target.width()
    height = target.height()
    if width <= 0 or height <= 0:
        return

    bg = background or QColor(BACKGROUND)
    painter = QPainter(target)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    if scroll_value > 0:
        top = QLinearGradient(0, 0, 0, fade_height)
        top.setColorAt(0.0, bg)
        top.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, width, fade_height, top)

    if scroll_value < scroll_max:
        bottom_start = height - fade_height
        bottom = QLinearGradient(0, bottom_start, 0, height)
        bottom.setColorAt(0.0, QColor(0, 0, 0, 0))
        bottom.setColorAt(1.0, bg)
        painter.fillRect(0, bottom_start, width, fade_height, bottom)

    painter.end()


class ScrollEdgeFadeOverlay(QWidget):
    def __init__(
        self,
        scroll_bar: QScrollBar,
        *,
        parent: QWidget,
        fade_height: int = ALPHABET_FADE_HEIGHT,
        background: QColor | None = None,
        should_fade: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self._scroll_bar = scroll_bar
        self._fade_height = fade_height
        self._background = background
        self._should_fade = should_fade or (lambda: scroll_bar.maximum() > 0)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        scroll_bar.valueChanged.connect(self._on_scroll_changed)
        scroll_bar.rangeChanged.connect(self._on_scroll_changed)

    def sync(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self.raise_()
        self.update()

    def _on_scroll_changed(self, *_args) -> None:
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        if not self._should_fade():
            return
        paint_scroll_edge_fades(
            self,
            scroll_value=self._scroll_bar.value(),
            scroll_max=self._scroll_bar.maximum(),
            fade_height=self._fade_height,
            background=self._background,
        )
