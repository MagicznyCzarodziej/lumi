"""Vector icons painted with QPainter."""

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QGuiApplication, QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_PLAY_CIRCLE = "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10s10-4.48 10-10S17.52 2 12 2zM9.5 16.5v-9l7 4.5l-7 4.5z"
_SEARCH = (
    "M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5"
    " 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0"
    "C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
)
_STAR = (
    "M22 9.24l-7.19-.62L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.63-7.03L22 9.24z"
    "M12 15.4l-3.76 2.27 1-4.28-3.32-2.88 4.38-.38L12 6.1l1.71 4.03 4.38.38-3.32 2.88 1 4.28L12 15.4z"
)
_AUTO_AWESOME_MOTION = (
    "M14 2H4c-1.1 0-2 .9-2 2v10h2V4h10V2zm4 4H8c-1.1 0-2 .9-2 2v10h2V8h10V6zm2 4h-8c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2v-8c0-1.1-.9-2-2-2zm0 10h-8v-8h8v8z"
)
_FOLDER_COPY = (
    "M3 19h17v2H3c-1.1 0-2-.9-2-2V6h2v13zM23 6v9c0 1.1-.9 2-2 2H7c-1.1 0-2-.9-2-2l.01-11c0-1.1.89-2 1.99-2h5l2 2h7c1.1 0 2 .9 2 2zM7 15h14V6h-7.83l-2-2H7v11z"
)
_SELL_OUTLINE = (
    "M21.41 11.41l-8.83-8.83c-.37-.37-.88-.58-1.41-.58H4c-1.1 0-2 .9-2 2v7.17c0 .53.21 1.04.59 1.41l8.83 8.83c.78.78 2.05.78 2.83 0"
    "l7.17-7.17c.78-.78.78-2.04-.01-2.83zM12.83 20L4 11.17V4h7.17L20 12.83L12.83 20z"
)
_REFRESH = (
    "M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8"
    "c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6"
    "c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"
)
_ANIMATION_PLAY = (
    "M4,2a2,2 0,0 0,-2 2v10h2L4,4h10L14,2zM8,6a2,2 0,0 0,-2 2v10h2L8,8h10L18,6z"
    "M20,12v8h-8v-8zM20,10h-8a2,2 0,0 0,-2 2v8a2,2 0,0 0,2 2h8a2,2 0,0 0,2 -2v-8a2,2 0,0 0,-2 -2m-6,3v6l4,-3z"
)


class IconKind(Enum):
    SEARCH = auto()
    STAR = auto()
    REFRESH = auto()
    SELL = auto()
    PLAY_CIRCLE = auto()
    SERIES = auto()
    FOLDER = auto()
    PLAYABLES = auto()


_SVG_PATHS: dict[IconKind, str] = {
    IconKind.SEARCH: _SEARCH,
    IconKind.STAR: _STAR,
    IconKind.PLAY_CIRCLE: _PLAY_CIRCLE,
    IconKind.REFRESH: _REFRESH,
    IconKind.SERIES: _AUTO_AWESOME_MOTION,
    IconKind.FOLDER: _FOLDER_COPY,
    IconKind.PLAYABLES: _ANIMATION_PLAY,
    IconKind.SELL: _SELL_OUTLINE,
}


def themed_icon(kind: IconKind, *, size: int = 24, color: str = "#80FFFFFF") -> QIcon:
    app = QGuiApplication.instance()
    dpr = float(app.devicePixelRatio()) if isinstance(app, QGuiApplication) else 1.0
    physical = max(1, round(size * dpr))
    pixmap = QPixmap(physical, physical)
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    paint_icon(painter, pixmap.rect(), kind, QColor(color))
    painter.end()
    return QIcon(pixmap)


def paint_icon(painter: QPainter, rect, kind: IconKind, color: QColor) -> None:
    _paint_svg_icon(painter, rect, kind, color)


def _svg_body(kind: IconKind, fill: str) -> str:
    path_d = _SVG_PATHS[kind]
    body = f'<path fill="{fill}" d="{path_d}"/>'
    if kind is IconKind.SELL:
        body += f'<circle fill="{fill}" cx="6.5" cy="6.5" r="1.5"/>'
    return body


def _paint_svg_icon(painter: QPainter, rect, kind: IconKind, color: QColor) -> None:
    fill = color.name(QColor.NameFormat.HexRgb)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        f"{_svg_body(kind, fill)}"
        f"</svg>"
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setOpacity(painter.opacity() * color.alphaF())
    renderer.render(painter, rect)
    painter.restore()
