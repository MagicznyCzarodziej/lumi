"""Transport cross, timeline bar, and corner hint geometry."""

from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QFontMetrics

from lumi.ui.player.overlay.layout.metrics import UiMetrics
from lumi.ui.player.overlay.layout.regions.fonts import time_label_width, ui_font


def layout_controls_geometry(
    w: int,
    h: int,
    m: UiMetrics,
    *,
    prev_ep: bool = False,
    next_ep: bool = False,
) -> tuple[dict[str, QRect], dict[str, QRect], QRect, QRect, QRect, int]:
    """Lay out CONTROLS / SCRUB chrome anchored to the bottom edge.

    The seek bar spans the full viewport width and sits flush with the bottom.
    Elapsed / total timestamps are placed in a row directly above the bar.
    Transport controls are centered horizontally above the time row.
    Corner hints stack on the left, vertically centered in the viewport.

    Returns ``(cross_regions, hint_regions, seek_inner, elapsed_rect, total_rect,
    time_font_size)``. Cross keys: ``m1``, ``center``, ``p1``.
    Hint keys: ``video``, ``subs``, ``audio``.
    """
    margin = m.margin

    time_font_size = min(m.font_md, m.font_sm + 3)
    time_font = ui_font(time_font_size, bold=True)
    fm = QFontMetrics(time_font)

    label_w = time_label_width(fm, 4)
    time_row_h = fm.height()
    time_gap = max(4, m.gap // 2)
    time_inset = max(6, int(w * 0.006))

    # Full-bleed seek bar flush with the bottom edge.
    bar_h = max(5, min(10, int(h * 0.01)))
    bar_y = h - bar_h
    seek_inner = QRect(0, bar_y, w, bar_h)

    # Elapsed / total sit in a row directly above the bar, hugging the side edges.
    time_row_bottom = bar_y - time_gap
    time_row_top = time_row_bottom - time_row_h
    elapsed_rect = QRect(time_inset, time_row_top, label_w, time_row_h)
    total_rect = QRect(w - time_inset - label_w, time_row_top, label_w, time_row_h)

    # Transport cross — centered above the time row.
    sizes = {"lg": m.btn_lg, "md": m.btn_md, "sm": m.btn_sm}
    gap = m.gap
    ep_side = sizes["sm"]
    ep_gap = gap + max(2, gap // 2)
    core_w = sizes["sm"] + sizes["lg"] + sizes["sm"] + gap * 2
    ep_w = (ep_side + ep_gap) if prev_ep else 0
    ep_w += (ep_side + ep_gap) if next_ep else 0
    total_cross_w = core_w + ep_w

    controls_gap = max(16, int(h * 0.022))
    controls_bottom = time_row_top - controls_gap
    cross_y = controls_bottom - sizes["lg"] // 2
    x = w // 2 - total_cross_w // 2

    cross_regions: dict[str, QRect] = {}
    if prev_ep:
        cross_regions["prev_ep"] = QRect(x, cross_y - ep_side // 2, ep_side, ep_side)
        x += ep_side + ep_gap
    for key, size_key in (
        ("m1", "sm"),
        ("center", "lg"),
        ("p1", "sm"),
    ):
        side = sizes[size_key]
        cross_regions[key] = QRect(x, cross_y - side // 2, side, side)
        x += side + gap
    if next_ep:
        cross_regions["next_ep"] = QRect(x, cross_y - ep_side // 2, ep_side, ep_side)

    # Corner hints — left column, vertically centered as a stack.
    hint_x = margin
    hint_side = m.hint_size
    label_line_h = max(14, m.font_sm) + 2
    track_line_h = max(14, m.font_sm - 1) + 2
    text_group_h = label_line_h + max(2, m.gap // 3) + track_line_h
    hint_block_h = max(hint_side, text_group_h)
    stack_h = hint_block_h * 3 + m.hint_gap * 2
    video_y = max(margin, (h - stack_h) // 2)
    subs_y = video_y + hint_block_h + m.hint_gap
    audio_y = subs_y + hint_block_h + m.hint_gap
    hint_regions = {
        "video": QRect(hint_x, video_y, hint_side, hint_side),
        "subs": QRect(hint_x, subs_y, hint_side, hint_side),
        "audio": QRect(hint_x, audio_y, hint_side, hint_side),
    }

    return cross_regions, hint_regions, seek_inner, elapsed_rect, total_rect, time_font_size
