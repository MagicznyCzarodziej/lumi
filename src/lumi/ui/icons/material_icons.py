"""Vector icons painted with QPainter."""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QRectF
from PySide6.QtGui import QGuiApplication, QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_EPISODE_ADVANCE_SVG = Path(__file__).resolve().parent / "episode_advance.svg"
_EPISODE_ADVANCE_VIEWBOX_W = 40.0
_EPISODE_ADVANCE_VIEWBOX_H = 30.0
EPISODE_ADVANCE_ASPECT = _EPISODE_ADVANCE_VIEWBOX_W / _EPISODE_ADVANCE_VIEWBOX_H

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
_SAVE = (
    "M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3"
    " 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z"
)
_DELETE = "M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
_ADD = "M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"
_REMOVE = "M19 13H5v-2h14v2z"
_CHEVRON_LEFT = "M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"
_CHEVRON_RIGHT = "M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"
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
    SAVE = auto()
    DELETE = auto()
    ADD = auto()
    REMOVE = auto()
    CHEVRON_LEFT = auto()
    CHEVRON_RIGHT = auto()
    EPISODE_NEXT = auto()
    EPISODE_PREVIOUS = auto()


_SVG_PATHS: dict[IconKind, str] = {
    IconKind.SEARCH: _SEARCH,
    IconKind.STAR: _STAR,
    IconKind.PLAY_CIRCLE: _PLAY_CIRCLE,
    IconKind.REFRESH: _REFRESH,
    IconKind.SERIES: _AUTO_AWESOME_MOTION,
    IconKind.FOLDER: _FOLDER_COPY,
    IconKind.PLAYABLES: _ANIMATION_PLAY,
    IconKind.SELL: _SELL_OUTLINE,
    IconKind.SAVE: _SAVE,
    IconKind.DELETE: _DELETE,
    IconKind.ADD: _ADD,
    IconKind.REMOVE: _REMOVE,
    IconKind.CHEVRON_LEFT: _CHEVRON_LEFT,
    IconKind.CHEVRON_RIGHT: _CHEVRON_RIGHT,
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
    if kind in (IconKind.EPISODE_NEXT, IconKind.EPISODE_PREVIOUS):
        _paint_episode_advance_icon(
            painter,
            rect,
            color,
            forward=kind is IconKind.EPISODE_NEXT,
        )
        return
    _paint_svg_icon(painter, rect, kind, color)


def _episode_advance_svg_bytes(color: QColor) -> bytes:
    fill = color.name(QColor.NameFormat.HexRgb)
    text = _EPISODE_ADVANCE_SVG.read_text(encoding="utf-8")
    tinted = text.replace('stroke="black"', f'stroke="{fill}"').replace('fill="black"', f'fill="{fill}"')
    return tinted.encode("utf-8")


def _episode_advance_render_rect(rect) -> QRectF:
    aspect = _EPISODE_ADVANCE_VIEWBOX_W / _EPISODE_ADVANCE_VIEWBOX_H
    if rect.width() / max(1.0, rect.height()) > aspect:
        height = rect.height()
        width = height * aspect
    else:
        width = rect.width()
        height = width / aspect
    x = rect.x() + (rect.width() - width) / 2
    y = rect.y() + (rect.height() - height) / 2
    return QRectF(x, y, width, height)


def _paint_episode_advance_icon(
    painter: QPainter,
    rect,
    color: QColor,
    *,
    forward: bool,
) -> None:
    renderer = QSvgRenderer(QByteArray(_episode_advance_svg_bytes(color)))
    target = _episode_advance_render_rect(rect)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setOpacity(painter.opacity() * color.alphaF())
    if forward:
        renderer.render(painter, target)
    else:
        painter.translate(target.x() + target.width(), target.y())
        painter.scale(-1, 1)
        renderer.render(painter, QRectF(0, 0, target.width(), target.height()))
    painter.restore()


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
