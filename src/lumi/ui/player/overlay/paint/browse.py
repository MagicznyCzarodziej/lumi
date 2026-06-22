"""Subtitle folder browser painting."""

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
from lumi.domain.subtitles.browse import BrowseEntryKind
from lumi.ui.player.overlay.state import OverlayState


def _elide_path(path_text: str, fm: QFontMetrics, max_width: int) -> str:
    if fm.horizontalAdvance(path_text) <= max_width:
        return path_text
    return fm.elidedText(path_text, Qt.TextElideMode.ElideMiddle, max_width)


def paint_browse_sheet(
    painter: QPainter,
    w: int,
    h: int,
    state: OverlayState,
    layout: LayoutSnapshot,
    *,
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
    path_font = ui_font(m.track_font - 1)
    painter.setFont(title_font)
    painter.setPen(QColor(WHITE))
    title_h = QFontMetrics(title_font).height()
    title_rect = QRect(px, py, panel_w - px * 2, title_h)
    painter.drawText(
        title_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        "Browse subtitles",
    )

    path_text = state.browse_path.as_posix() if state.browse_path is not None else ""
    path_y = py + title_h + 4
    path_h = QFontMetrics(path_font).height()
    path_rect = QRect(px, path_y, panel_w - px * 2, path_h)
    painter.setFont(path_font)
    painter.setPen(QColor.fromRgbF(1, 1, 1, 0.55))
    painter.drawText(
        path_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        _elide_path(path_text, QFontMetrics(path_font), path_rect.width()),
    )

    rows = state.browse_rows or []
    item_font = ui_font(m.track_font)
    item_font_bold = ui_font(m.track_font, bold=True)
    list_clip = None
    if layout.panel_list_bottom > layout.panel_list_top:
        list_clip = QRect(0, layout.panel_list_top, panel_w, layout.panel_list_bottom - layout.panel_list_top)
    if list_clip is not None:
        painter.save()
        painter.setClipRect(list_clip)
    for i, row in enumerate(rows):
        rect = layout.hit_regions.get(f"browse:{i}")
        if rect is None or rect.isEmpty():
            continue
        foc = i == state.browse_focus
        strength = press_strength if f"browse:{i}" == press_key else 0.0
        if strength > 0:
            paint_accent_press_overlay(painter, rect, strength)
            paint_press_overlay(painter, rect, strength)
            bar = QColor(ACCENT)
            bar.setAlpha(int(255 * strength))
            painter.fillRect(0, rect.y(), m.accent_bar_w, rect.height(), bar)
        elif foc:
            painter.fillRect(rect, QColor.fromRgbF(1, 1, 1, 0.14))
            painter.fillRect(0, rect.y(), m.accent_bar_w, rect.height(), QColor(ACCENT))

        if row.kind == BrowseEntryKind.DIRECTORY:
            painter.setPen(QColor.fromRgbF(0.72, 0.82, 1.0, 0.95 if foc else 0.82))
        elif row.kind == BrowseEntryKind.PARENT:
            painter.setPen(QColor.fromRgbF(1, 1, 1, 0.72))
        else:
            painter.setPen(QColor(WHITE) if foc else QColor.fromRgbF(1, 1, 1, 0.88))

        draw_font = item_font_bold if foc else item_font
        text_rect = rect.adjusted(m.track_pad_x, 0, -m.track_pad_x, 0)
        painter.setFont(draw_font)
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            row.label,
        )
    if list_clip is not None:
        painter.restore()
