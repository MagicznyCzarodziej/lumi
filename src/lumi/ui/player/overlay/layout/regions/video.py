"""Video aspect drawer layout."""

from __future__ import annotations

from PySide6.QtGui import QFontMetrics

from lumi.domain.video_aspect import VIDEO_ASPECT_MODES, video_aspect_label
from lumi.ui.player.overlay.layout.metrics import UiMetrics
from lumi.ui.player.overlay.layout.regions.fonts import ui_font
from lumi.ui.player.overlay.layout.regions.scroll_list import ScrollListLayout, layout_scrolling_rows
from lumi.ui.player.overlay.layout.regions.tracks import track_row_height


def video_panel_width(w: int, m: UiMetrics) -> int:
    """Fit panel to “Video” title and widest aspect-mode label."""
    item_font = ui_font(m.track_font, bold=True)
    title_font = ui_font(m.track_title_font, bold=True)
    fm_item = QFontMetrics(item_font)
    fm_title = QFontMetrics(title_font)
    labels = [video_aspect_label(mode) for mode in VIDEO_ASPECT_MODES]
    content_w = fm_title.horizontalAdvance("Video")
    if labels:
        content_w = max(content_w, max(fm_item.horizontalAdvance(label) for label in labels))
    needed = content_w + m.track_pad_x * 2 + m.accent_bar_w + 12
    return max(m.panel_w_min, min(w - m.margin, needed))


def layout_video_panel(
    *,
    w: int,
    h: int,
    m: UiMetrics,
    panel_scroll_y: int,
) -> tuple[int, ScrollListLayout]:
    """Lay out the video aspect picker drawer. Row keys are ``video:{index}``."""
    panel_w = video_panel_width(w, m)
    title_font = ui_font(m.track_title_font, bold=True)
    title_h = QFontMetrics(title_font).height()
    text_w = panel_w - m.track_pad_x * 2
    list_top = m.track_pad_y + title_h + m.track_pad_y // 2
    list_bottom = h - m.track_pad_y

    row_heights = [
        (f"video:{index}", track_row_height(video_aspect_label(mode), m, text_w))
        for index, mode in enumerate(VIDEO_ASPECT_MODES)
    ]
    scroll = layout_scrolling_rows(
        list_top=list_top,
        list_bottom=list_bottom,
        panel_w=panel_w,
        panel_scroll_y=panel_scroll_y,
        rows=row_heights,
    )
    return panel_w, scroll
