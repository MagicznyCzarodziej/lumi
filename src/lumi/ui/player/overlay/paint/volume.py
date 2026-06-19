"""Volume indicator painting."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter

from lumi.ui.player.overlay.paint.primitives import WHITE, ui_font


def paint_volume(painter: QPainter, w: int, h: int, volume: float, *, muted: bool = False) -> None:
    vol = volume
    x = w - max(24, int(w * 0.04))
    bar_h = max(60, min(120, int(h * 0.12)))
    y = h - max(80, int(h * 0.12)) - bar_h
    bar_w = 6
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor.fromRgbF(1, 1, 1, 0.18))
    painter.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)
    fill_h = 0 if muted else int(bar_h * vol / 100)
    if fill_h:
        painter.setBrush(QColor(WHITE) if vol else QColor.fromRgbF(1, 1, 1, 0.35))
        painter.drawRoundedRect(x, y + bar_h - fill_h, bar_w, fill_h, 3, 3)
    painter.setFont(ui_font(11, bold=True))
    painter.setPen(QColor.fromRgbF(1, 1, 1, 0.7))
    label = "M" if muted else str(int(vol))
    painter.drawText(
        QRect(x - 12, y + bar_h + 6, 32, 20),
        int(Qt.AlignmentFlag.AlignCenter),
        label,
    )
