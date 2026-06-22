"""Layout geometry and hit regions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics

from lumi.ui.player.overlay.layout.metrics import UiMetrics, compute_ui_metrics
from lumi.ui.player.overlay.layout.panel_scroll import clamp_panel_scroll
from lumi.domain.subtitles.browse import BrowseRow
from lumi.domain.video_aspect import VIDEO_ASPECT_MODES, video_aspect_label
from lumi.ui.player.overlay.state import TrackKind, TrackRow, View, is_footer_button


class HitRegion(str, Enum):
    OPEN = "open"
    M1 = "m1"
    M10 = "m10"
    CENTER = "center"
    P10 = "p10"
    P1 = "p1"
    SUBS = "subs"
    AUDIO = "audio"
    VIDEO = "video"
    SEEK = "seek"


def ui_font(size: int, bold: bool = False) -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    font.setPointSize(max(9, size))
    font.setBold(bold)
    return font


def time_label_width(fm: QFontMetrics, gap: int) -> int:
    sample_w = max(
        fm.horizontalAdvance("0:00"),
        fm.horizontalAdvance("0:00:00"),
        fm.horizontalAdvance("99:59:59"),
    )
    return sample_w + gap


@dataclass
class LayoutSnapshot:
    hit_regions: dict[str, QRect]
    seek_inner: QRect
    elapsed_rect: QRect
    total_rect: QRect
    panel_w: int
    time_font_size: int
    metrics: UiMetrics
    track_footer_top: int | None = None
    panel_scroll_y: int = 0
    panel_scroll_max: int = 0
    panel_list_top: int = 0
    panel_list_bottom: int = 0
    panel_row_tops: dict[str, int] = field(default_factory=dict)


def layout_idle_regions(w: int, h: int) -> dict[str, QRect]:
    btn_w, btn_h = 180, 44
    return {"open": QRect((w - btn_w) // 2, h // 2 + 20, btn_w, btn_h)}


def layout_controls_geometry(
    w: int, h: int, m: UiMetrics
) -> tuple[dict[str, QRect], dict[str, QRect], QRect, QRect, QRect, int]:
    margin = m.margin
    bottom_pad = m.bottom_pad

    time_font_size = m.font_sm
    time_font = ui_font(m.font_sm, bold=True)
    fm = QFontMetrics(time_font)

    label_gap = 6
    label_w = time_label_width(fm, 4)

    bar_h = max(6, min(14, int(h * 0.012)))

    row_bottom = h - bottom_pad
    bar_y = row_bottom - bar_h
    row_h = max(fm.height(), bar_h, max(16, min(36, int(m.scale * 0.028))))
    row_top = bar_y - (row_h - bar_h) // 2

    elapsed_rect = QRect(margin, row_top, label_w, row_h)
    total_rect = QRect(w - margin - label_w, row_top, label_w, row_h)

    bar_x = margin + label_w + label_gap
    bar_w = w - 2 * margin - 2 * label_w - 2 * label_gap
    seek_inner = QRect(bar_x, bar_y, max(48, bar_w), bar_h)

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

    cross_top = cross_y - sizes["lg"] // 2
    hint_x = margin
    label_line_h = max(14, m.font_sm) + 2
    track_line_h = max(14, m.font_sm - 1) + 2
    text_group_h = label_line_h + max(2, m.gap // 3) + track_line_h
    hint_block_h = max(m.hint_size, text_group_h)
    audio_y = cross_top - m.gap - hint_block_h
    subs_y = audio_y - m.hint_gap - hint_block_h
    video_y = max(m.margin, subs_y - m.hint_gap - hint_block_h)
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


def track_action_icon_size(m: UiMetrics) -> int:
    return max(28, min(36, m.track_row_h - 12))


def track_action_icons_width(m: UiMetrics, *, count: int = 2) -> int:
    size = track_action_icon_size(m)
    gap = max(6, m.gap // 2)
    return m.track_pad_x + count * size + max(0, count - 1) * gap + m.track_pad_x // 2


def track_row_has_action_icons(track_rows: list[TrackRow]) -> bool:
    return any(row.show_napi_save or row.show_napi_delete for row in track_rows)


def split_track_panel_rows(track_rows: list[TrackRow]) -> tuple[list[tuple[int, TrackRow]], list[tuple[int, TrackRow]]]:
    entries: list[tuple[int, TrackRow]] = []
    footer: list[tuple[int, TrackRow]] = []
    for index, row in enumerate(track_rows):
        if row.is_action:
            footer.append((index, row))
        else:
            entries.append((index, row))
    return entries, footer


def track_footer_button_height(m: UiMetrics) -> int:
    return max(44, int(m.track_row_h * 0.78))


def track_sub_delay_row_height(m: UiMetrics) -> int:
    return max(40, int(m.track_row_h * 0.72))


def track_footer_status_height(label: str, m: UiMetrics, text_w: int) -> int:
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
    total = m.gap
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


def track_footer_block_height(
    footer_rows: list[tuple[int, TrackRow]],
    m: UiMetrics,
    panel_w: int,
) -> int:
    return track_footer_extent_height(footer_rows, m, panel_w)


def track_panel_width(
    w: int,
    m: UiMetrics,
    track_kind: TrackKind,
    track_rows: list[TrackRow],
) -> int:
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


def browse_row_height(label: str, m: UiMetrics) -> int:
    fm = QFontMetrics(ui_font(m.track_font, bold=True))
    return max(m.track_row_h, fm.height() + 12)


def browse_panel_width(
    w: int,
    m: UiMetrics,
    browse_path: PurePosixPath | None,
    browse_rows: list[BrowseRow],
) -> int:
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


def video_panel_width(w: int, m: UiMetrics) -> int:
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


def compute_layout(
    w: int,
    h: int,
    view: View,
    track_kind: TrackKind,
    track_rows: list[TrackRow],
    *,
    browse_path: PurePosixPath | None = None,
    browse_rows: list[BrowseRow] | None = None,
    panel_scroll_y: int = 0,
) -> LayoutSnapshot:
    metrics = compute_ui_metrics(w, h)
    hit_regions: dict[str, QRect] = {}
    seek_inner = QRect()
    elapsed_rect = QRect()
    total_rect = QRect()
    time_font_size = metrics.font_sm
    panel_w = metrics.panel_w_min
    track_footer_top: int | None = None
    panel_scroll_max = 0
    panel_list_top = 0
    panel_list_bottom = h
    panel_row_tops: dict[str, int] = {}
    scroll_y = panel_scroll_y

    if view in (View.CONTROLS, View.SCRUB):
        cross, hints, seek_inner, elapsed_rect, total_rect, time_font_size = (
            layout_controls_geometry(w, h, metrics)
        )
        if view == View.CONTROLS:
            hit_regions.update(cross)
            hit_regions.update(hints)
        hit_regions["seek"] = seek_inner.adjusted(
            0,
            -metrics.btn_sm // 3,
            0,
            metrics.btn_sm // 3,
        )
    elif view == View.TRACKS:
        panel_w = track_panel_width(w, metrics, track_kind, track_rows)
        title_font = ui_font(metrics.track_title_font, bold=True)
        title_h = QFontMetrics(title_font).height()
        text_w = panel_w - metrics.track_pad_x * 2
        list_top = metrics.track_pad_y + title_h + metrics.track_pad_y // 2
        entries, footer = split_track_panel_rows(track_rows)

        content_y = list_top
        entry_specs: list[tuple[int, TrackRow, int, int]] = []
        for index, row in entries:
            icons_w = (
                track_action_icons_width(metrics)
                if row.show_napi_save or row.show_napi_delete
                else 0
            )
            row_h = track_row_height(row.label, metrics, text_w - icons_w)
            entry_specs.append((index, row, content_y, row_h))
            content_y += row_h

        if footer:
            footer_h = track_footer_extent_height(footer, metrics, panel_w)
            footer_bottom_pad = metrics.track_pad_x
            track_footer_top = h - footer_bottom_pad - footer_h
            list_bottom = track_footer_top - metrics.gap
        else:
            list_bottom = h - metrics.track_pad_y

        content_height = max(0, content_y - list_top)
        viewport_height = max(0, list_bottom - list_top)
        panel_scroll_max = max(0, content_height - viewport_height)
        scroll_y = clamp_panel_scroll(scroll_y, panel_scroll_max)
        panel_list_top = list_top
        panel_list_bottom = list_bottom

        for index, row, row_top, row_h in entry_specs:
            screen_y = row_top - scroll_y
            panel_row_tops[f"track:{index}"] = row_top
            hit_regions[f"track:{index}"] = QRect(0, screen_y, panel_w, row_h)
            if row.show_napi_save or row.show_napi_delete:
                size = track_action_icon_size(metrics)
                gap = max(6, metrics.gap // 2)
                icon_y = screen_y + (row_h - size) // 2
                icon_x = panel_w - metrics.track_pad_x - size
                if row.show_napi_delete:
                    hit_regions[f"track:{index}:delete"] = QRect(icon_x, icon_y, size, size)
                    icon_x -= size + gap
                if row.show_napi_save:
                    hit_regions[f"track:{index}:save"] = QRect(icon_x, icon_y, size, size)

        if footer:
            btn_h = track_footer_button_height(metrics)
            btn_x = metrics.track_pad_x
            btn_w = panel_w - metrics.track_pad_x * 2
            gap = max(8, metrics.gap // 2)
            y = track_footer_top + metrics.gap
            for i, (index, row) in enumerate(footer):
                if is_footer_button(row):
                    hit_regions[f"track:{index}"] = QRect(btn_x, y, btn_w, btn_h)
                    y += btn_h
                    if i < len(footer) - 1:
                        y += gap
                elif row.is_sub_delay_control:
                    row_h = track_sub_delay_row_height(metrics)
                    hit_regions[f"track:{index}"] = QRect(btn_x, y, btn_w, row_h)
                    size = track_action_icon_size(metrics)
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
                    status_h = track_footer_status_height(row.label, metrics, btn_w)
                    hit_regions[f"track:{index}"] = QRect(btn_x, y, btn_w, status_h)
                    y += status_h
                    if i < len(footer) - 1:
                        y += gap // 2
    elif view == View.VIDEO:
        panel_w = video_panel_width(w, metrics)
        title_font = ui_font(metrics.track_title_font, bold=True)
        title_h = QFontMetrics(title_font).height()
        text_w = panel_w - metrics.track_pad_x * 2
        list_top = metrics.track_pad_y + title_h + metrics.track_pad_y // 2
        list_bottom = h - metrics.track_pad_y

        content_y = list_top
        row_specs: list[tuple[int, int, int]] = []
        for index, mode in enumerate(VIDEO_ASPECT_MODES):
            row_h = track_row_height(video_aspect_label(mode), metrics, text_w)
            row_specs.append((index, content_y, row_h))
            content_y += row_h

        content_height = max(0, content_y - list_top)
        viewport_height = max(0, list_bottom - list_top)
        panel_scroll_max = max(0, content_height - viewport_height)
        scroll_y = clamp_panel_scroll(scroll_y, panel_scroll_max)
        panel_list_top = list_top
        panel_list_bottom = list_bottom

        for index, row_top, row_h in row_specs:
            screen_y = row_top - scroll_y
            panel_row_tops[f"video:{index}"] = row_top
            hit_regions[f"video:{index}"] = QRect(0, screen_y, panel_w, row_h)
    elif view == View.SUBTITLE_BROWSE:
        rows = browse_rows or []
        panel_w = browse_panel_width(w, metrics, browse_path, rows)
        title_font = ui_font(metrics.track_title_font, bold=True)
        path_font = ui_font(metrics.track_font - 1)
        title_h = QFontMetrics(title_font).height()
        path_h = QFontMetrics(path_font).height()
        list_top = metrics.track_pad_y + title_h + path_h + 8 + metrics.track_pad_y // 4
        list_bottom = h - metrics.track_pad_y

        content_y = list_top
        row_specs: list[tuple[int, int, int]] = []
        for i, browse_row in enumerate(rows):
            row_h = browse_row_height(browse_row.label, metrics)
            row_specs.append((i, content_y, row_h))
            content_y += row_h

        content_height = max(0, content_y - list_top)
        viewport_height = max(0, list_bottom - list_top)
        panel_scroll_max = max(0, content_height - viewport_height)
        scroll_y = clamp_panel_scroll(scroll_y, panel_scroll_max)
        panel_list_top = list_top
        panel_list_bottom = list_bottom

        for i, row_top, row_h in row_specs:
            screen_y = row_top - scroll_y
            panel_row_tops[f"browse:{i}"] = row_top
            hit_regions[f"browse:{i}"] = QRect(0, screen_y, panel_w, row_h)

    return LayoutSnapshot(
        hit_regions=hit_regions,
        seek_inner=seek_inner,
        elapsed_rect=elapsed_rect,
        total_rect=total_rect,
        panel_w=panel_w,
        time_font_size=time_font_size,
        metrics=metrics,
        track_footer_top=track_footer_top,
        panel_scroll_y=scroll_y,
        panel_scroll_max=panel_scroll_max,
        panel_list_top=panel_list_top,
        panel_list_bottom=panel_list_bottom,
        panel_row_tops=panel_row_tops,
    )
