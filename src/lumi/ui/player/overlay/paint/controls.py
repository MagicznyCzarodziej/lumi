"""Cross transport controls and timeline painting."""

from __future__ import annotations

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QFontMetrics, QLinearGradient, QPainter, QPen

from lumi.ui.player.overlay.layout.metrics import fmt_time
from lumi.ui.player.overlay.layout.regions import LayoutSnapshot
from lumi.ui.player.overlay.paint.primitives import (
    ACCENT,
    UNFOCUSED_SCRUB_FILL,
    paint_cell,
    paint_cell_label,
    paint_episode_skip_icon,
    paint_play_icon,
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
    track_bg = QColor.fromRgbF(1, 1, 1, 0.36) if timeline_focused else UNFOCUSED_SCRUB_FILL
    progress = QColor(ACCENT) if timeline_focused else QColor.fromRgbF(1, 1, 1, 0.62)
    playhead_color = QColor(ACCENT) if timeline_focused else QColor.fromRgbF(1, 1, 1, 0.88)
    time_color = QColor(255, 255, 255)

    time_font = ui_font(layout.time_font_size, bold=True)
    painter.setFont(time_font)
    painter.setPen(time_color)
    painter.drawText(
        layout.elapsed_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        fmt_time(state.time_pos),
    )
    painter.drawText(
        layout.total_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
        fmt_time(state.duration),
    )

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(track_bg)
    painter.drawRect(inner)

    fill_w = int(inner.width() * pct)
    if fill_w > 0:
        painter.setBrush(progress)
        painter.drawRect(inner.x(), inner.y(), fill_w, inner.height())

    playhead_x = inner.x() + fill_w if fill_w > 0 else inner.x()
    playhead_x = min(max(inner.x(), playhead_x), inner.right())
    tick_w = max(5, min(8, int(m.scale * 0.006)))
    tick_h = max(20, min(32, int(m.scale * 0.026)))
    tick_x = playhead_x - tick_w // 2
    tick_rect = QRect(tick_x, inner.top() - tick_h, tick_w, tick_h)
    tick_radius = tick_w // 2
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(playhead_color)
    painter.drawRoundedRect(tick_rect, tick_radius, tick_radius)


_CROSS_KEYS = frozenset(
    {"m1", "center", "p1", "prev_ep", "next_ep"},
)


def _paint_controls_backdrop(
    painter: QPainter,
    *,
    viewport_w: int,
    viewport_h: int,
    layout: LayoutSnapshot,
) -> None:
    cross_rects = [
        layout.hit_regions[k] for k in _CROSS_KEYS if k in layout.hit_regions
    ]
    if not cross_rects:
        return
    pad = layout.metrics.gap
    top = min(r.top() for r in cross_rects) - pad * 2
    top = max(0, top)
    grad = QLinearGradient(0.0, float(top), 0.0, float(viewport_h))
    grad.setColorAt(0.0, QColor.fromRgbF(0, 0, 0, 0.0))
    grad.setColorAt(0.45, QColor.fromRgbF(0, 0, 0, 0.28))
    grad.setColorAt(1.0, QColor.fromRgbF(0, 0, 0, 0.62))
    painter.fillRect(0, top, viewport_w, viewport_h - top, grad)


def paint_cross_controls(
    painter: QPainter,
    state: OverlayState,
    layout: LayoutSnapshot,
    *,
    playing: bool,
    press_key: str | None = None,
    press_strength: float = 0.0,
    viewport_w: int | None = None,
    viewport_h: int | None = None,
) -> None:
    m = layout.metrics
    if viewport_w is not None and viewport_h is not None:
        _paint_controls_backdrop(
            painter,
            viewport_w=viewport_w,
            viewport_h=viewport_h,
            layout=layout,
        )

    for key, rect in layout.hit_regions.items():
        if key in {"seek", "subs", "audio", "video"}:
            continue
        on_focus = key == state.cross_focus and state.focus_zone == FocusZone.CONTROLS
        strength = press_strength if key == press_key else 0.0
        paint_cell(painter, rect, on_focus, press_strength=strength)
        if key == "center":
            paint_play_icon(painter, rect, playing, on_focus)
        elif key == "prev_ep":
            paint_episode_skip_icon(painter, rect, forward=False, on_focus=on_focus)
        elif key == "next_ep":
            paint_episode_skip_icon(painter, rect, forward=True, on_focus=on_focus)
        elif key in ("m1", "p1"):
            paint_cell_label(
                painter,
                rect,
                "−1s" if key == "m1" else "+1s",
                max(m.font_sm, int(rect.height() * 0.26)),
                on_focus,
            )
    timeline_focused = state.focus_zone == FocusZone.TIMELINE
    paint_timeline(
        painter,
        state,
        layout,
        timeline_focused=timeline_focused,
    )


def paint_episode_title(
    painter: QPainter,
    layout: LayoutSnapshot,
    *,
    title: str | None,
    viewport_w: int,
) -> None:
    if not title:
        return
    m = layout.metrics
    font = ui_font(m.track_title_font, bold=True)
    fm = QFontMetrics(font)
    max_w = max(200, int(viewport_w * 0.55))
    text = fm.elidedText(title, Qt.TextElideMode.ElideRight, max_w)
    top = max(8, m.margin // 3)
    text_rect = QRect(m.margin, top, max_w, fm.height() + 8)
    shadow = QColor.fromRgbF(0, 0, 0, 0.35)
    text_color = QColor.fromRgbF(1, 1, 1, 0.58)
    painter.setFont(font)
    painter.setPen(shadow)
    painter.drawText(
        text_rect.translated(1, 1),
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        text,
    )
    painter.setPen(text_color)
    painter.drawText(
        text_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        text,
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
