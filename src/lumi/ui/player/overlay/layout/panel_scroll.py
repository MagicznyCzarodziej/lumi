"""Scroll math for side-panel drawer lists."""

from __future__ import annotations


def clamp_panel_scroll(scroll_y: int, max_scroll: int) -> int:
    if max_scroll <= 0:
        return 0
    return max(0, min(scroll_y, max_scroll))


def scroll_to_show_item(
    item_top: int,
    item_height: int,
    *,
    viewport_top: int,
    viewport_bottom: int,
    scroll_y: int,
) -> int:
    if item_height <= 0:
        return scroll_y
    visible_top = item_top - scroll_y
    visible_bottom = visible_top + item_height
    if visible_top < viewport_top:
        return item_top - viewport_top
    if visible_bottom > viewport_bottom:
        return item_top + item_height - viewport_bottom
    return scroll_y
