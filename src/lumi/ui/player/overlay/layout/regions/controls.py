"""Transport cross, timeline bar, and corner hint geometry."""

from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QFontMetrics

from lumi.ui.player.overlay.layout.metrics import UiMetrics
from lumi.ui.player.overlay.layout.regions.fonts import time_label_width, ui_font


def layout_controls_geometry(
    w: int, h: int, m: UiMetrics
) -> tuple[dict[str, QRect], dict[str, QRect], QRect, QRect, QRect, int]:
    """Lay out CONTROLS / SCRUB chrome anchored to the bottom edge.

    Returns ``(cross_regions, hint_regions, seek_inner, elapsed_rect, total_rect,
    time_font_size)``. Cross keys: ``m1``, ``m10``, ``center``, ``p10``, ``p1``.
    Hint keys: ``video``, ``subs``, ``audio``.
    """
    margin = m.margin
    bottom_pad = m.bottom_pad

    time_font_size = m.font_sm
    time_font = ui_font(m.font_sm, bold=True)
    fm = QFontMetrics(time_font)

    label_gap = 6
    label_w = time_label_width(fm, 4)

    # Thin seek bar; height scales slightly with viewport.
    bar_h = max(6, min(14, int(h * 0.012)))

    # Timeline row: labels flank the bar; row is tall enough for touch targets.
    row_bottom = h - bottom_pad
    bar_y = row_bottom - bar_h
    row_h = max(fm.height(), bar_h, max(16, min(36, int(m.scale * 0.028))))
    row_top = bar_y - (row_h - bar_h) // 2

    elapsed_rect = QRect(margin, row_top, label_w, row_h)
    total_rect = QRect(w - margin - label_w, row_top, label_w, row_h)

    bar_x = margin + label_w + label_gap
    bar_w = w - 2 * margin - 2 * label_w - 2 * label_gap
    seek_inner = QRect(bar_x, bar_y, max(48, bar_w), bar_h)

    # Transport cross — sm/md/lg buttons, centered above the timeline.
    sizes = {"lg": m.btn_lg, "md": m.btn_md, "sm": m.btn_sm}
    gap = m.gap
    total_cross_w = sizes["sm"] + sizes["md"] + sizes["lg"] + sizes["md"] + sizes["sm"] + gap * 4

    cross_gap = max(20, int(h * 0.025))
    cross_bottom = row_top - cross_gap
    cross_y = cross_bottom - sizes["lg"] // 2
    cx = w // 2
    x = cx - total_cross_w // 2

    cross_regions: dict[str, QRect] = {}
    for key, size_key in (
        ("m1", "sm"),
        ("m10", "md"),
        ("center", "lg"),
        ("p10", "md"),
        ("p1", "sm"),
    ):
        side = sizes[size_key]
        cross_regions[key] = QRect(x, cross_y - side // 2, side, side)
        x += side + gap

    # Corner hints stack above the cross (video → subs → audio, top to bottom).
    cross_top = cross_y - sizes["lg"] // 2
    hint_x = margin
    label_line_h = max(14, m.font_sm) + 2
    track_line_h = max(14, m.font_sm - 1) + 2
    text_group_h = label_line_h + max(2, m.gap // 3) + track_line_h
    hint_block_h = max(m.hint_size, text_group_h)
    audio_y = cross_top - m.gap - hint_block_h
    subs_y = audio_y - m.hint_gap - hint_block_h
    video_y = max(m.margin, subs_y - m.hint_gap - hint_block_h)
    # On short viewports, compress the stack so hints stay above the cross.
    if video_y + hint_block_h * 3 + m.hint_gap * 2 > cross_top:
        video_y = max(m.margin, cross_top - hint_block_h * 3 - m.hint_gap * 2)
        subs_y = video_y + hint_block_h + m.hint_gap
        audio_y = subs_y + hint_block_h + m.hint_gap
    hint_regions = {
        "video": QRect(hint_x, video_y, m.hint_size, m.hint_size),
        "subs": QRect(hint_x, subs_y, m.hint_size, m.hint_size),
        "audio": QRect(hint_x, audio_y, m.hint_size, m.hint_size),
    }

    return cross_regions, hint_regions, seek_inner, elapsed_rect, total_rect, time_font_size
