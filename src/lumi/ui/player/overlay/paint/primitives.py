"""Shared paint primitives and colors."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPolygon,
    QRadialGradient,
)

ACCENT = "#3b82f6"
FOCUS_FILL = QColor(37, 99, 235, 255)
CIRCLE_FILL_ALPHA = 77
FOCUS_CIRCLE_ALPHA = 255
UNFOCUSED_SCRUB_FILL = QColor.fromRgbF(1, 1, 1, 0.26)
TEXT_DARK = QColor(24, 24, 28)
TEXT_LIGHT = QColor(255, 255, 255)
WHITE = "#ffffff"
PRESS_OVERLAY_ALPHA = 88
PRESS_ACCENT_ALPHA = 58

def _antialiased_ellipse_rect(rect: QRect) -> QRectF:
    """Half-pixel inset so ellipse edges land on device pixels when AA is on."""
    return QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)


def ui_font(size: int, bold: bool = False) -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    font.setPointSize(max(9, size))
    font.setBold(bold)
    return font


def seek_fill_path(x: int, y: int, w: int, h: int, radius: int) -> QPainterPath:
    path = QPainterPath()
    if w <= 0:
        return path
    if w <= radius * 2:
        path.addEllipse(QRectF(x, y, w, h))
        return path
    path.moveTo(x + radius, y)
    path.lineTo(x + w, y)
    path.lineTo(x + w, y + h)
    path.lineTo(x + radius, y + h)
    path.arcTo(x, y, radius * 2, h, 90, 180)
    path.closeSubpath()
    return path


def paint_press_overlay(
    painter: QPainter,
    rect: QRect,
    strength: float,
    *,
    radius: int | None = None,
    ellipse: bool = False,
    max_alpha: int = PRESS_OVERLAY_ALPHA,
) -> None:
    """Animated highlight — background only, no border."""
    if strength <= 0.0:
        return
    overlay = QColor(255, 255, 255)
    overlay.setAlpha(int(max_alpha * strength))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(overlay)
    if ellipse:
        painter.drawEllipse(_antialiased_ellipse_rect(rect))
    elif radius is not None:
        painter.drawRoundedRect(QRectF(rect), radius, radius)
    else:
        painter.fillRect(rect, overlay)


def paint_accent_press_overlay(
    painter: QPainter,
    rect: QRect,
    strength: float,
    *,
    radius: int | None = None,
    ellipse: bool = False,
    max_alpha: int = PRESS_ACCENT_ALPHA,
) -> None:
    if strength <= 0.0:
        return
    accent = QColor(ACCENT)
    accent.setAlpha(int(max_alpha * strength))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(accent)
    if ellipse:
        painter.drawEllipse(_antialiased_ellipse_rect(rect))
    elif radius is not None:
        painter.drawRoundedRect(QRectF(rect), radius, radius)
    else:
        painter.fillRect(rect, accent)


def _cell_fill_gradient(
    base: QColor, cx: float, cy: float, radius: float, *, fill_alpha: int
) -> QRadialGradient:
    """Solid fill with only a few pixels of soft alpha at the outer edge."""
    fade_px = max(4.0, min(6.0, radius * 0.07))
    grad_radius = radius + 0.5
    edge = radius / grad_radius
    fade_start = max(0.0, (radius - fade_px) / grad_radius)
    r, g, b = base.red(), base.green(), base.blue()
    solid = QColor(r, g, b, fill_alpha)
    clear = QColor(r, g, b, 0)
    gradient = QRadialGradient(QPointF(cx, cy), grad_radius)
    gradient.setColorAt(0.0, solid)
    gradient.setColorAt(fade_start, solid)
    gradient.setColorAt(edge, clear)
    gradient.setColorAt(1.0, clear)
    return gradient


def paint_cell(
    painter: QPainter,
    rect: QRect,
    focused: bool,
    *,
    press_strength: float = 0.0,
) -> None:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    ellipse = _antialiased_ellipse_rect(rect)
    cx = ellipse.center().x()
    cy = ellipse.center().y()
    radius = min(ellipse.width(), ellipse.height()) / 2.0

    if focused:
        base = QColor(255, 255, 255)
        fill_alpha = FOCUS_CIRCLE_ALPHA
    else:
        base = QColor(0, 0, 0)
        fill_alpha = CIRCLE_FILL_ALPHA

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_cell_fill_gradient(base, cx, cy, radius, fill_alpha=fill_alpha))
    painter.drawEllipse(ellipse)
    paint_accent_press_overlay(painter, rect, press_strength, ellipse=True)
    paint_press_overlay(painter, rect, press_strength, ellipse=True)


def paint_cell_label(
    painter: QPainter,
    rect: QRect,
    text: str,
    size: int,
    on_focus: bool,
) -> None:
    pad = max(8, int(min(rect.width(), rect.height()) * 0.2))
    inner = rect.adjusted(pad, pad, -pad, -pad)
    font = ui_font(size, bold=True)
    fm = QFontMetrics(font)
    while size > 9 and fm.horizontalAdvance(text) > inner.width():
        size -= 1
        font = ui_font(size, bold=True)
        fm = QFontMetrics(font)
    painter.setFont(font)
    painter.setPen(TEXT_DARK if on_focus else TEXT_LIGHT)
    painter.drawText(inner, int(Qt.AlignmentFlag.AlignCenter), text)


def paint_play_icon(painter: QPainter, rect: QRect, playing: bool, on_focus: bool) -> None:
    icon_color = TEXT_DARK if on_focus else TEXT_LIGHT
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(icon_color)
    cx, cy = rect.center().x(), rect.center().y()
    size = min(rect.width(), rect.height())

    if playing:
        bar_w = max(5, int(size * 0.1))
        bar_h = max(16, int(size * 0.32))
        gap = max(5, int(size * 0.08))
        bar_radius = max(2, bar_w // 2)
        total_w = bar_w * 2 + gap
        x0 = cx - total_w // 2
        y0 = cy - bar_h // 2
        painter.drawRoundedRect(x0, y0, bar_w, bar_h, bar_radius, bar_radius)
        painter.drawRoundedRect(x0 + bar_w + gap, y0, bar_w, bar_h, bar_radius, bar_radius)
    else:
        half_h = size * 0.18
        half_w = size * 0.21
        left = cx - half_w * 0.3
        tri = QPolygon(
            [
                QPoint(int(left), int(cy - half_h)),
                QPoint(int(left), int(cy + half_h)),
                QPoint(int(left + half_w * 1.15), int(cy)),
            ]
        )
        painter.drawPolygon(tri)


def paint_episode_skip_icon(
    painter: QPainter,
    rect: QRect,
    *,
    forward: bool,
    on_focus: bool,
) -> None:
    """Previous/next episode — sized to match play/pause glyph scale."""
    from lumi.ui.icons.material_icons import (
        EPISODE_ADVANCE_ASPECT,
        IconKind,
        paint_icon,
    )

    color = TEXT_DARK if on_focus else TEXT_LIGHT
    kind = IconKind.EPISODE_NEXT if forward else IconKind.EPISODE_PREVIOUS
    size = min(rect.width(), rect.height())
    icon_h = size * 0.38
    icon_w = icon_h * EPISODE_ADVANCE_ASPECT
    cx, cy = rect.center().x(), rect.center().y()
    inner = QRect(int(cx - icon_w / 2), int(cy - icon_h / 2), int(icon_w), int(icon_h))
    paint_icon(painter, inner, kind, color)
