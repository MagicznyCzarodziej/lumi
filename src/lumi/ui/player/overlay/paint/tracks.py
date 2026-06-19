"""Track sidebar painting."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen

from lumi.ui.player.overlay.layout.regions import LayoutSnapshot
from lumi.ui.player.overlay.paint.primitives import (
    ACCENT,
    WHITE,
    paint_accent_press_overlay,
    paint_press_overlay,
    ui_font,
)
from lumi.ui.player.overlay.state import OverlayState, TrackKind, selected_track_index


def paint_track_sheet(
    painter: QPainter,
    w: int,
    h: int,
    state: OverlayState,
    layout: LayoutSnapshot,
    *,
    sid: int | None,
    aid: int | None,
    press_key: str | None = None,
    press_strength: float = 0.0,
) -> None:
    m = layout.metrics
    panel_w = layout.panel_w
    panel = QRect(0, 0, panel_w, h)
    painter.fillRect(panel, QColor.fromRgbF(0.08, 0.08, 0.1, 0.96))
    painter.setPen(QPen(QColor.fromRgbF(1, 1, 1, 0.1)))
    painter.drawLine(panel_w, 0, panel_w, h)

    px = m.track_pad_x
    py = m.track_pad_y
    title_font = ui_font(m.track_title_font, bold=True)
    painter.setFont(title_font)
    painter.setPen(QColor(WHITE))
    title = "Subtitles" if state.track_kind == TrackKind.SUBTITLES else "Audio"
    title_h = QFontMetrics(title_font).height()
    title_rect = QRect(px, py, panel_w - px * 2, title_h)
    painter.drawText(
        title_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        title,
    )

    selected = selected_track_index(state, sid, aid)
    rows = state.track_rows or []
    item_font = ui_font(m.track_font)
    item_font_bold = ui_font(m.track_font, bold=True)
    for i, (_tid, label) in enumerate(rows):
        row = layout.hit_regions.get(f"track:{i}")
        if row is None or row.isEmpty():
            continue
        on = i == selected
        foc = i == state.track_focus
        strength = press_strength if f"track:{i}" == press_key else 0.0
        if strength > 0:
            paint_accent_press_overlay(painter, row, strength)
            paint_press_overlay(painter, row, strength)
            bar = QColor(ACCENT)
            bar.setAlpha(int(255 * strength))
            painter.fillRect(0, row.y(), m.accent_bar_w, row.height(), bar)
        elif foc:
            painter.fillRect(row, QColor.fromRgbF(1, 1, 1, 0.14))
            painter.fillRect(0, row.y(), m.accent_bar_w, row.height(), QColor(ACCENT))
        elif on:
            painter.fillRect(row, QColor.fromRgbF(1, 1, 1, 0.08))
            painter.fillRect(
                0,
                row.y(),
                m.accent_bar_w,
                row.height(),
                QColor.fromRgbF(1, 1, 1, 0.4),
            )
        draw_font = item_font_bold if on else item_font
        text_rect = row.adjusted(m.track_pad_x, 0, -m.track_pad_x, 0)
        if on or foc:
            painter.setPen(QColor(WHITE))
        else:
            painter.setPen(QColor.fromRgbF(1, 1, 1, 0.88))
        painter.setFont(draw_font)
        painter.drawText(
            text_rect,
            int(
                Qt.AlignmentFlag.AlignVCenter
                | Qt.AlignmentFlag.AlignLeft
                | Qt.TextFlag.TextWordWrap
            ),
            label,
        )
