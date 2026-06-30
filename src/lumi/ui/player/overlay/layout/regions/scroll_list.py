"""Shared scrollable list layout for simple drawer panels (video, browse)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRect

from lumi.ui.player.overlay.layout.panel_scroll import clamp_panel_scroll


@dataclass(frozen=True)
class ScrollListLayout:
    """Scroll state + hit regions for a single-column row list."""

    hit_regions: dict[str, QRect]
    panel_row_tops: dict[str, int]
    panel_scroll_y: int
    panel_scroll_max: int
    panel_list_top: int
    panel_list_bottom: int


def layout_scrolling_rows(
    *,
    list_top: int,
    list_bottom: int,
    panel_w: int,
    panel_scroll_y: int,
    rows: list[tuple[str, int]],
) -> ScrollListLayout:
    """Place fixed-height rows in a vertically scrollable viewport.

    ``rows`` is ``(region_key, row_height)`` in display order.
    ``panel_row_tops`` stores content-space Y; ``hit_regions`` are screen-space
    (content Y minus ``panel_scroll_y``).
    """
    # Pass 1: assign content-space tops while stacking downward.
    content_y = list_top
    row_specs: list[tuple[str, int, int]] = []
    for key, row_h in rows:
        row_specs.append((key, content_y, row_h))
        content_y += row_h

    content_height = max(0, content_y - list_top)
    viewport_height = max(0, list_bottom - list_top)
    panel_scroll_max = max(0, content_height - viewport_height)
    scroll_y = clamp_panel_scroll(panel_scroll_y, panel_scroll_max)

    # Pass 2: convert to screen-space hit rects for mouse routing.
    hit_regions: dict[str, QRect] = {}
    panel_row_tops: dict[str, int] = {}
    for key, row_top, row_h in row_specs:
        screen_y = row_top - scroll_y
        panel_row_tops[key] = row_top
        hit_regions[key] = QRect(0, screen_y, panel_w, row_h)

    return ScrollListLayout(
        hit_regions=hit_regions,
        panel_row_tops=panel_row_tops,
        panel_scroll_y=scroll_y,
        panel_scroll_max=panel_scroll_max,
        panel_list_top=list_top,
        panel_list_bottom=list_bottom,
    )
