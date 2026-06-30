"""Subtitle folder browse drawer layout."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtGui import QFontMetrics

from lumi.domain.subtitles.browse import BrowseRow
from lumi.ui.player.overlay.layout.metrics import UiMetrics
from lumi.ui.player.overlay.layout.regions.fonts import ui_font
from lumi.ui.player.overlay.layout.regions.scroll_list import ScrollListLayout, layout_scrolling_rows


def browse_row_height(label: str, m: UiMetrics) -> int:
    """Single-line browse entry height (directories and subtitle files)."""
    fm = QFontMetrics(ui_font(m.track_font, bold=True))
    return max(m.track_row_h, fm.height() + 12)


def browse_panel_width(
    w: int,
    m: UiMetrics,
    browse_path: PurePosixPath | None,
    browse_rows: list[BrowseRow],
) -> int:
    """Fit panel to title, current path string, and widest row label."""
    item_font = ui_font(m.track_font, bold=True)
    title_font = ui_font(m.track_title_font, bold=True)
    path_font = ui_font(m.track_font - 1)
    fm_item = QFontMetrics(item_font)
    fm_title = QFontMetrics(title_font)
    fm_path = QFontMetrics(path_font)
    labels = [row.label for row in browse_rows]
    content_w = fm_title.horizontalAdvance("Browse subtitles")
    if browse_path is not None:
        content_w = max(content_w, fm_path.horizontalAdvance(browse_path.as_posix()))
    if labels:
        content_w = max(content_w, max(fm_item.horizontalAdvance(label) for label in labels))
    needed = content_w + m.track_pad_x * 2 + m.accent_bar_w + 12
    return max(m.panel_w_min, min(w, needed))


def layout_browse_panel(
    *,
    w: int,
    h: int,
    m: UiMetrics,
    browse_path: PurePosixPath | None,
    browse_rows: list[BrowseRow],
    panel_scroll_y: int,
) -> tuple[int, ScrollListLayout]:
    """Lay out the subtitle file browser drawer.

    Header (title + path) sits above the scrollable row list. Row keys are
    ``browse:{index}`` matching ``InputRouter`` and ``paint/browse.py``.
    """
    panel_w = browse_panel_width(w, m, browse_path, browse_rows)
    title_font = ui_font(m.track_title_font, bold=True)
    path_font = ui_font(m.track_font - 1)
    title_h = QFontMetrics(title_font).height()
    path_h = QFontMetrics(path_font).height()
    # list_top is below the painted title and path lines.
    list_top = m.track_pad_y + title_h + path_h + 8 + m.track_pad_y // 4
    list_bottom = h - m.track_pad_y

    row_heights = [
        (f"browse:{i}", browse_row_height(row.label, m))
        for i, row in enumerate(browse_rows)
    ]
    scroll = layout_scrolling_rows(
        list_top=list_top,
        list_bottom=list_bottom,
        panel_w=panel_w,
        panel_scroll_y=panel_scroll_y,
        rows=row_heights,
    )
    return panel_w, scroll
