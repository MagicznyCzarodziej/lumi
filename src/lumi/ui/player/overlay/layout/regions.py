"""Layout geometry and hit regions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics

from lumi.ui.player.overlay.layout.metrics import UiMetrics, compute_ui_metrics
from lumi.ui.player.overlay.state import TrackKind, View


class HitRegion(str, Enum):
    OPEN = "open"
    M1 = "m1"
    M10 = "m10"
    CENTER = "center"
    P10 = "p10"
    P1 = "p1"
    SUBS = "subs"
    AUDIO = "audio"
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
    subs_y = max(m.margin, audio_y - m.hint_gap - hint_block_h)
    if subs_y + hint_block_h * 2 + m.hint_gap > cross_top:
        subs_y = max(m.margin, cross_top - hint_block_h * 2 - m.hint_gap)
        audio_y = subs_y + hint_block_h + m.hint_gap
    hint_regions = {
        "subs": QRect(hint_x, subs_y, m.hint_size, m.hint_size),
        "audio": QRect(hint_x, audio_y, m.hint_size, m.hint_size),
    }

    return cross_regions, hint_regions, seek_inner, elapsed_rect, total_rect, time_font_size


def track_panel_width(
    w: int,
    m: UiMetrics,
    track_kind: TrackKind,
    track_rows: list[tuple[int | None, str]],
) -> int:
    item_font = ui_font(m.track_font, bold=True)
    title_font = ui_font(m.track_title_font, bold=True)
    fm_item = QFontMetrics(item_font)
    fm_title = QFontMetrics(title_font)
    title = "Subtitles" if track_kind == TrackKind.SUBTITLES else "Audio"
    labels = [label for _, label in track_rows]
    content_w = fm_title.horizontalAdvance(title)
    if labels:
        content_w = max(content_w, max(fm_item.horizontalAdvance(label) for label in labels))
    needed = content_w + m.track_pad_x * 2 + m.accent_bar_w + 12
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


def compute_layout(
    w: int,
    h: int,
    view: View,
    track_kind: TrackKind,
    track_rows: list[tuple[int | None, str]],
) -> LayoutSnapshot:
    metrics = compute_ui_metrics(w, h)
    hit_regions: dict[str, QRect] = {}
    seek_inner = QRect()
    elapsed_rect = QRect()
    total_rect = QRect()
    time_font_size = metrics.font_sm
    panel_w = metrics.panel_w_min

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
        y = metrics.track_pad_y + title_h + metrics.track_pad_y // 2
        for i, (_tid, label) in enumerate(track_rows):
            row_h = track_row_height(label, metrics, text_w)
            hit_regions[f"track:{i}"] = QRect(0, y, panel_w, row_h)
            y += row_h

    return LayoutSnapshot(
        hit_regions=hit_regions,
        seek_inner=seek_inner,
        elapsed_rect=elapsed_rect,
        total_rect=total_rect,
        panel_w=panel_w,
        time_font_size=time_font_size,
        metrics=metrics,
    )
