"""Track drawer layout — entries, footer actions, and Napi icon hit targets."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QFontMetrics

from lumi.ui.player.overlay.layout.metrics import UiMetrics
from lumi.ui.player.overlay.layout.panel_scroll import clamp_panel_scroll
from lumi.ui.player.overlay.layout.regions.fonts import ui_font
from lumi.ui.player.overlay.state import TrackKind, TrackRow, is_footer_button


def track_action_icon_size(m: UiMetrics) -> int:
    """Save/delete icon square — fits inside a track row with padding."""
    return max(28, min(36, m.track_row_h - 12))


def track_action_icons_width(m: UiMetrics, *, count: int = 2) -> int:
    """Horizontal space reserved at the right edge for Napi action icons."""
    size = track_action_icon_size(m)
    gap = max(6, m.gap // 2)
    return m.track_pad_x + count * size + max(0, count - 1) * gap + m.track_pad_x // 2


def track_row_has_action_icons(track_rows: list[TrackRow]) -> bool:
    """Whether any row shows save/delete icons (affects panel width)."""
    return any(row.show_napi_save or row.show_napi_delete for row in track_rows)


def split_track_panel_rows(track_rows: list[TrackRow]) -> tuple[list[tuple[int, TrackRow]], list[tuple[int, TrackRow]]]:
    """Split scrollable track entries from the pinned footer block.

    Footer rows (Browse, Napi download, delay controls) keep their original
    ``track:{index}`` keys so command handlers stay stable.
    """
    entries: list[tuple[int, TrackRow]] = []
    footer: list[tuple[int, TrackRow]] = []
    for index, row in enumerate(track_rows):
        if row.is_action:
            footer.append((index, row))
        else:
            entries.append((index, row))
    return entries, footer


def track_footer_button_height(m: UiMetrics) -> int:
    """Full-width footer buttons (Browse, Download from NapiProjekt)."""
    return max(44, int(m.track_row_h * 0.78))


def track_sub_delay_row_height(m: UiMetrics) -> int:
    """Footer row with earlier/later delay icon buttons."""
    return max(40, int(m.track_row_h * 0.72))


def track_footer_status_height(label: str, m: UiMetrics, text_w: int) -> int:
    """Wrapped status text (e.g. Napi download message) in the footer."""
    fm = QFontMetrics(ui_font(max(12, m.track_font - 4)))
    bounds = fm.boundingRect(
        0,
        0,
        text_w,
        10000,
        int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignHCenter),
        label,
    )
    return max(24, bounds.height() + 8)


def track_footer_extent_height(
    footer_rows: list[tuple[int, TrackRow]],
    m: UiMetrics,
    panel_w: int,
) -> int:
    """Height from the separator line to the bottom of the last footer row."""
    if not footer_rows:
        return 0
    text_w = panel_w - m.track_pad_x * 2
    btn_h = track_footer_button_height(m)
    gap = max(8, m.gap // 2)
    total = m.gap  # gap below the separator line
    for i, (_index, row) in enumerate(footer_rows):
        if is_footer_button(row):
            total += btn_h
            if i < len(footer_rows) - 1:
                total += gap
        elif row.is_sub_delay_control:
            total += track_sub_delay_row_height(m)
            if i < len(footer_rows) - 1:
                total += gap
        else:
            total += track_footer_status_height(row.label, m, text_w)
            if i < len(footer_rows) - 1:
                total += gap // 2
    return total


def track_panel_width(
    w: int,
    m: UiMetrics,
    track_kind: TrackKind,
    track_rows: list[TrackRow],
) -> int:
    """Shrink-to-fit panel width from title, labels, icons, and footer buttons."""
    item_font = ui_font(m.track_font, bold=True)
    title_font = ui_font(m.track_title_font, bold=True)
    fm_item = QFontMetrics(item_font)
    fm_title = QFontMetrics(title_font)
    title = "Subtitles" if track_kind == TrackKind.SUBTITLES else "Audio"
    entry_rows, footer_rows = split_track_panel_rows(track_rows)
    entry_labels = [row.label for _index, row in entry_rows]
    footer_labels = [row.label for _index, row in footer_rows if is_footer_button(row)]
    labels = entry_labels + footer_labels
    content_w = fm_title.horizontalAdvance(title)
    if labels:
        content_w = max(content_w, max(fm_item.horizontalAdvance(label) for label in labels))
    button_extra = track_footer_button_height(m) if footer_labels else 0
    icons_w = (
        track_action_icons_width(m)
        if track_row_has_action_icons(track_rows)
        else 0
    )
    needed = content_w + m.track_pad_x * 2 + m.accent_bar_w + icons_w + button_extra + 12
    return max(m.panel_w_min, min(w - m.margin, needed))


def track_row_height(label: str, m: UiMetrics, text_w: int) -> int:
    """Entry row height — grows when the track label wraps to multiple lines."""
    fm = QFontMetrics(ui_font(m.track_font, bold=True))
    bounds = fm.boundingRect(
        0,
        0,
        text_w,
        10000,
        int(Qt.TextFlag.TextWordWrap),
        label,
    )
    return max(m.track_row_h, bounds.height() + 12)


@dataclass(frozen=True)
class TrackPanelLayout:
    """Layout result for the track drawer (entries scroll; footer pins to bottom)."""

    panel_w: int
    hit_regions: dict[str, QRect]
    panel_row_tops: dict[str, int]
    panel_scroll_y: int
    panel_scroll_max: int
    panel_list_top: int
    panel_list_bottom: int
    track_footer_top: int | None


def layout_track_panel(
    *,
    w: int,
    h: int,
    m: UiMetrics,
    track_kind: TrackKind,
    track_rows: list[TrackRow],
    panel_scroll_y: int,
) -> TrackPanelLayout:
    """Lay out the subtitle/audio track drawer.

    Scrollable mpv track entries sit between ``panel_list_top`` and
    ``panel_list_bottom``. Footer actions pin below that viewport at
    ``track_footer_top``. Only entries scroll; footer hit targets ignore
    ``panel_scroll_y``.
    """
    panel_w = track_panel_width(w, m, track_kind, track_rows)
    title_font = ui_font(m.track_title_font, bold=True)
    title_h = QFontMetrics(title_font).height()
    text_w = panel_w - m.track_pad_x * 2
    list_top = m.track_pad_y + title_h + m.track_pad_y // 2
    entries, footer = split_track_panel_rows(track_rows)

    # Stack entry rows in content space (unscrolled Y).
    content_y = list_top
    entry_specs: list[tuple[int, TrackRow, int, int]] = []
    for index, row in entries:
        # Narrower text area when save/delete icons occupy the right edge.
        icons_w = (
            track_action_icons_width(m)
            if row.show_napi_save or row.show_napi_delete
            else 0
        )
        row_h = track_row_height(row.label, m, text_w - icons_w)
        entry_specs.append((index, row, content_y, row_h))
        content_y += row_h

    # Pin footer to the bottom; scrollable area ends above the separator gap.
    track_footer_top: int | None
    if footer:
        footer_h = track_footer_extent_height(footer, m, panel_w)
        footer_bottom_pad = m.track_pad_x
        track_footer_top = h - footer_bottom_pad - footer_h
        list_bottom = track_footer_top - m.gap
    else:
        track_footer_top = None
        list_bottom = h - m.track_pad_y

    content_height = max(0, content_y - list_top)
    viewport_height = max(0, list_bottom - list_top)
    panel_scroll_max = max(0, content_height - viewport_height)
    scroll_y = clamp_panel_scroll(panel_scroll_y, panel_scroll_max)

    hit_regions: dict[str, QRect] = {}
    panel_row_tops: dict[str, int] = {}
    for index, row, row_top, row_h in entry_specs:
        screen_y = row_top - scroll_y
        panel_row_tops[f"track:{index}"] = row_top
        hit_regions[f"track:{index}"] = QRect(0, screen_y, panel_w, row_h)
        if row.show_napi_save or row.show_napi_delete:
            size = track_action_icon_size(m)
            gap = max(6, m.gap // 2)
            icon_y = screen_y + (row_h - size) // 2
            icon_x = panel_w - m.track_pad_x - size
            # Icons are right-aligned; delete is outermost.
            if row.show_napi_delete:
                hit_regions[f"track:{index}:delete"] = QRect(icon_x, icon_y, size, size)
                icon_x -= size + gap
            if row.show_napi_save:
                hit_regions[f"track:{index}:save"] = QRect(icon_x, icon_y, size, size)

    if footer:
        assert track_footer_top is not None
        btn_h = track_footer_button_height(m)
        btn_x = m.track_pad_x
        btn_w = panel_w - m.track_pad_x * 2
        gap = max(8, m.gap // 2)
        y = track_footer_top + m.gap
        for i, (index, row) in enumerate(footer):
            if is_footer_button(row):
                hit_regions[f"track:{index}"] = QRect(btn_x, y, btn_w, btn_h)
                y += btn_h
                if i < len(footer) - 1:
                    y += gap
            elif row.is_sub_delay_control:
                row_h = track_sub_delay_row_height(m)
                hit_regions[f"track:{index}"] = QRect(btn_x, y, btn_w, row_h)
                size = track_action_icon_size(m)
                icon_y = y + (row_h - size) // 2
                hit_regions[f"track:{index}:delay-earlier"] = QRect(btn_x, icon_y, size, size)
                hit_regions[f"track:{index}:delay-later"] = QRect(
                    btn_x + btn_w - size,
                    icon_y,
                    size,
                    size,
                )
                y += row_h
                if i < len(footer) - 1:
                    y += gap
            else:
                status_h = track_footer_status_height(row.label, m, btn_w)
                hit_regions[f"track:{index}"] = QRect(btn_x, y, btn_w, status_h)
                y += status_h
                if i < len(footer) - 1:
                    y += gap // 2

    return TrackPanelLayout(
        panel_w=panel_w,
        hit_regions=hit_regions,
        panel_row_tops=panel_row_tops,
        panel_scroll_y=scroll_y,
        panel_scroll_max=panel_scroll_max,
        panel_list_top=list_top,
        panel_list_bottom=list_bottom,
        track_footer_top=track_footer_top,
    )
