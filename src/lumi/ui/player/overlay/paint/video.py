"""Video settings sidebar painting."""

from __future__ import annotations

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen

from lumi.domain.video_aspect import VIDEO_ASPECT_MODES, video_aspect_label
from lumi.ui.player.overlay.layout.regions import LayoutSnapshot
from lumi.ui.player.overlay.paint.primitives import ACCENT, WHITE, paint_press_overlay, ui_font
from lumi.ui.player.overlay.state import OverlayState


def paint_video_sheet(
    painter: QPainter,
    w: int,
    h: int,
    state: OverlayState,
    layout: LayoutSnapshot,
    *,
    current_mode_index: int,
    press_key: str | None = None,
    press_strength: float = 0.0,
) -> None:
    m = layout.metrics
    panel_w = layout.panel_w
    painter.fillRect(0, 0, panel_w, h, QColor.fromRgbF(0.08, 0.08, 0.1, 0.96))
    painter.setPen(QPen(QColor.fromRgbF(1, 1, 1, 0.1)))
    painter.drawLine(panel_w, 0, panel_w, h)

    px = m.track_pad_x
    py = m.track_pad_y
    title_font = ui_font(m.track_title_font, bold=True)
    painter.setFont(title_font)
    painter.setPen(QColor(WHITE))
    title_h = QFontMetrics(title_font).height()
    painter.drawText(
        px,
        py,
        panel_w - px * 2,
        title_h,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        "Video",
    )

    item_font = ui_font(m.track_font)
    item_font_bold = ui_font(m.track_font, bold=True)
    list_clip = None
    if layout.panel_list_bottom > layout.panel_list_top:
        list_clip = QRect(0, layout.panel_list_top, panel_w, layout.panel_list_bottom - layout.panel_list_top)
    if list_clip is not None:
        painter.save()
        painter.setClipRect(list_clip)

    for index, mode in enumerate(VIDEO_ASPECT_MODES):
        rect = layout.hit_regions.get(f"video:{index}")
        if rect is None:
            continue
        selected = index == current_mode_index
        focused = index == state.video_focus
        strength = press_strength if press_key == f"video:{index}" else 0.0
        if focused or selected or strength > 0:
            alpha = 0.14 if selected else 0.1 if focused else 0.06
            painter.fillRect(rect, QColor.fromRgbF(1, 1, 1, alpha))
        if focused or selected:
            painter.fillRect(0, rect.y(), m.accent_bar_w, rect.height(), QColor(ACCENT))
        if strength > 0:
            paint_press_overlay(painter, rect, strength)

        painter.setFont(item_font_bold if selected else item_font)
        painter.setPen(QColor(WHITE) if selected or focused else QColor.fromRgbF(1, 1, 1, 0.88))
        text_rect = rect.adjusted(px + m.accent_bar_w, 0, -px, 0)
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            video_aspect_label(mode),
        )
    if list_clip is not None:
        painter.restore()
