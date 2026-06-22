"""Cross transport controls and timeline painting."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen

from lumi.ui.player.overlay.layout.metrics import fmt_time
from lumi.ui.player.overlay.layout.regions import LayoutSnapshot
from lumi.ui.player.overlay.paint.primitives import (
    ACCENT,
    UNFOCUSED_SCRUB_FILL,
    WHITE,
    paint_cell,
    paint_cell_label,
    paint_play_icon,
    seek_fill_path,
    ui_font,
)
from lumi.ui.player.overlay.state import FocusZone, OverlayState


def paint_timeline(
    painter: QPainter,
    state: OverlayState,
    layout: LayoutSnapshot,
    *,
    timeline_focused: bool,
) -> None:
    pct = 0.0 if not state.duration else max(0.0, min(1.0, state.time_pos / state.duration))
    m = layout.metrics
    inner = layout.seek_inner
    radius = max(3, inner.height() // 2)
    track_bg = QColor.fromRgbF(1, 1, 1, 0.36) if timeline_focused else UNFOCUSED_SCRUB_FILL
    progress = QColor(ACCENT) if timeline_focused else QColor.fromRgbF(1, 1, 1, 0.62)
    dot_border = QColor(ACCENT) if timeline_focused else QColor.fromRgbF(1, 1, 1, 0.72)
    dot_fill = QColor(WHITE) if timeline_focused else QColor.fromRgbF(0.94, 0.94, 0.96)
    time_color = QColor(255, 255, 255)
    elapsed_color = time_color
    total_color = time_color

    if timeline_focused:
        painter.setPen(QPen(QColor(ACCENT), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(inner, radius, radius)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(track_bg)
    painter.drawRoundedRect(inner, radius, radius)

    fill_w = int(inner.width() * pct)
    if fill_w >= inner.width():
        painter.setBrush(progress)
        painter.drawRoundedRect(inner, radius, radius)
    elif fill_w > 0:
        painter.setBrush(progress)
        painter.drawPath(seek_fill_path(inner.x(), inner.y(), fill_w, inner.height(), radius))

    dot = max(16, min(36, int(m.scale * 0.028)))
    dot_x = inner.x() + fill_w if fill_w > 0 else inner.x()
    dot_x = min(max(inner.x(), dot_x), inner.right())
    dot_rect = inner.__class__(dot_x - dot // 2, inner.center().y() - dot // 2, dot, dot)
    painter.setBrush(dot_fill)
    painter.setPen(QPen(dot_border, 2))
    painter.drawEllipse(dot_rect)

    time_font = ui_font(layout.time_font_size, bold=True)
    painter.setFont(time_font)
    painter.setPen(elapsed_color)
    painter.drawText(
        layout.elapsed_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        fmt_time(state.time_pos),
    )
    painter.setPen(total_color)
    painter.drawText(
        layout.total_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
        fmt_time(state.duration),
    )


def paint_cross_controls(
    painter: QPainter,
    state: OverlayState,
    layout: LayoutSnapshot,
    *,
    playing: bool,
    press_key: str | None = None,
    press_strength: float = 0.0,
) -> None:
    m = layout.metrics

    for key, rect in layout.hit_regions.items():
        if key in {"seek", "subs", "audio", "video"}:
            continue
        on_focus = key == state.cross_focus and state.focus_zone == FocusZone.CONTROLS
        strength = press_strength if key == press_key else 0.0
        paint_cell(painter, rect, on_focus, press_strength=strength)
        if key == "center":
            paint_play_icon(painter, rect, playing, on_focus)
        elif key in ("m1", "p1"):
            paint_cell_label(
                painter,
                rect,
                "−1s" if key == "m1" else "+1s",
                m.font_sm,
                on_focus,
            )
        elif key in ("m10", "p10"):
            paint_cell_label(
                painter,
                rect,
                "−10s" if key == "m10" else "+10s",
                m.font_sm + (m.font_md - m.font_sm),
                on_focus,
            )

    timeline_focused = state.focus_zone == FocusZone.TIMELINE
    paint_timeline(
        painter,
        state,
        layout,
        timeline_focused=timeline_focused,
    )


def paint_corner_hints(
    painter: QPainter,
    layout: LayoutSnapshot,
    *,
    subtitle_name: str,
    audio_name: str,
    video_name: str,
) -> None:
    m = layout.metrics
    label_font = ui_font(m.font_sm, bold=True)
    label_fm = QFontMetrics(label_font)
    label_line_h = label_fm.height()
    track_font = ui_font(max(9, m.font_sm - 1))
    track_fm = QFontMetrics(track_font)
    track_line_h = track_fm.height()
    name_gap = max(2, m.gap // 3)
    text_w = max(int(m.scale * 0.22), 120)
    text_group_h = label_line_h + name_gap + track_line_h

    for hit_key, letter, label, track_name in (
        ("video", "V", "Video", video_name),
        ("subs", "S", "Subs", subtitle_name),
        ("audio", "A", "Audio", audio_name),
    ):
        badge = layout.hit_regions.get(hit_key)
        if badge is None:
            continue
        painter.setPen(QPen(QColor.fromRgbF(1, 1, 1, 0.5), 1))
        painter.setBrush(QColor.fromRgbF(0.08, 0.12, 0.22, 0.2))
        painter.drawRoundedRect(badge, m.radius_sm, m.radius_sm)

        letter_font = ui_font(m.font_md, bold=True)
        painter.setFont(letter_font)
        painter.setPen(QColor.fromRgbF(1, 1, 1, 0.85))
        painter.drawText(badge, int(Qt.AlignmentFlag.AlignCenter), letter)

        text_x = badge.right() + m.hint_label_gap
        group_top = badge.center().y() - text_group_h // 2
        label_rect = badge.__class__(text_x, group_top, text_w, label_line_h)
        name_rect = badge.__class__(
            text_x,
            group_top + label_line_h + name_gap,
            text_w,
            track_line_h,
        )

        painter.setFont(label_font)
        painter.setPen(QColor.fromRgbF(1, 1, 1, 0.82))
        painter.drawText(
            label_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            label,
        )

        painter.setFont(track_font)
        painter.setPen(QColor.fromRgbF(1, 1, 1, 0.58))
        name_rect.setWidth(max(text_w, track_fm.horizontalAdvance(track_name)))
        painter.drawText(
            name_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            track_name,
        )
