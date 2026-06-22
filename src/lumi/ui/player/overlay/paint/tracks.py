"""Track sidebar painting."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen

from lumi.domain.subtitles.delay import format_sub_delay
from lumi.ui.icons.material_icons import IconKind, paint_icon
from lumi.ui.player.overlay.layout.regions import LayoutSnapshot
from lumi.ui.player.overlay.paint.primitives import (
    ACCENT,
    TEXT_DARK,
    TEXT_LIGHT,
    WHITE,
    paint_accent_press_overlay,
    paint_cell,
    paint_press_overlay,
    ui_font,
)
from lumi.ui.player.overlay.state import (
    OverlayState,
    TrackKind,
    TrackRow,
    is_footer_button,
    selected_track_index,
)

_ACTION_ICONS: dict[str, IconKind] = {
    "save": IconKind.SAVE,
    "delete": IconKind.DELETE,
}

_DELAY_ARROW_ICONS: dict[str, IconKind] = {
    "delay-earlier": IconKind.CHEVRON_LEFT,
    "delay-later": IconKind.CHEVRON_RIGHT,
}

_FOOTER_ICONS: dict[str, IconKind] = {
    "download": IconKind.REFRESH,
    "browse": IconKind.FOLDER,
}


def _paint_sub_delay_control(
    painter: QPainter,
    state: OverlayState,
    layout: LayoutSnapshot,
    row_index: int,
    *,
    sub_delay: float,
    press_key: str | None,
    press_strength: float,
) -> None:
    rect = layout.hit_regions.get(f"track:{row_index}")
    if rect is None or rect.isEmpty():
        return
    m = layout.metrics
    focused = row_index == state.track_focus
    strength = press_strength if press_key == f"track:{row_index}" else 0.0
    if focused or strength > 0:
        painter.fillRect(rect, QColor.fromRgbF(1, 1, 1, 0.1 if focused else 0.06))
        if focused:
            painter.fillRect(0, rect.y(), m.accent_bar_w, rect.height(), QColor(ACCENT))

    label_font = ui_font(max(12, m.track_font - 5))
    value_font = ui_font(max(14, m.track_font - 3), bold=True)
    label_rect = QRect(
        rect.x() + m.track_pad_x,
        rect.y(),
        rect.width() - m.track_pad_x * 2,
        rect.height() // 2 + 4,
    )
    value_rect = QRect(
        rect.x() + m.track_pad_x,
        rect.y() + rect.height() // 2 - 4,
        rect.width() - m.track_pad_x * 2,
        rect.height() // 2 + 4,
    )
    painter.setFont(label_font)
    painter.setPen(QColor.fromRgbF(1, 1, 1, 0.62))
    painter.drawText(
        label_rect,
        int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter),
        "Delay",
    )
    painter.setFont(value_font)
    painter.setPen(QColor(WHITE) if focused else QColor.fromRgbF(1, 1, 1, 0.9))
    painter.drawText(
        value_rect,
        int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter),
        format_sub_delay(sub_delay),
    )

    for action in _DELAY_ARROW_ICONS:
        key = f"track:{row_index}:{action}"
        icon_rect = layout.hit_regions.get(key)
        if icon_rect is None or icon_rect.isEmpty():
            continue
        icon_strength = press_strength if press_key == key else 0.0
        if icon_strength > 0:
            paint_cell(
                painter,
                icon_rect,
                focused=True,
                press_strength=icon_strength,
            )
        icon_color = (
            QColor(WHITE)
            if focused or icon_strength > 0
            else QColor.fromRgbF(1, 1, 1, 0.72)
        )
        pad = max(4, icon_rect.width() // 6)
        paint_icon(
            painter,
            icon_rect.adjusted(pad, pad, -pad, -pad),
            _DELAY_ARROW_ICONS[action],
            icon_color,
        )


def _paint_track_action_icons(
    painter: QPainter,
    state: OverlayState,
    layout: LayoutSnapshot,
    row_index: int,
    track_row: TrackRow,
    *,
    press_key: str | None,
    press_strength: float,
    row_active: bool,
) -> None:
    if not track_row.show_napi_save and not track_row.show_napi_delete:
        return
    for action in ("save", "delete"):
        if action == "save" and not track_row.show_napi_save:
            continue
        if action == "delete" and not track_row.show_napi_delete:
            continue
        key = f"track:{row_index}:{action}"
        rect = layout.hit_regions.get(key)
        if rect is None or rect.isEmpty():
            continue
        strength = press_strength if press_key == key else 0.0
        icon_focused = (
            row_index == state.track_focus and state.track_action_focus == action
        )
        if strength > 0 or icon_focused:
            paint_cell(
                painter,
                rect,
                focused=icon_focused,
                press_strength=strength,
            )
        icon_color = TEXT_DARK if icon_focused else (
            TEXT_LIGHT if row_active or strength > 0 else QColor.fromRgbF(1, 1, 1, 0.82)
        )
        pad = max(4, rect.width() // 6)
        paint_icon(
            painter,
            rect.adjusted(pad, pad, -pad, -pad),
            _ACTION_ICONS[action],
            icon_color,
        )


def _paint_footer_button(
    painter: QPainter,
    layout: LayoutSnapshot,
    row_index: int,
    track_row: TrackRow,
    state: OverlayState,
    *,
    press_key: str | None,
    press_strength: float,
) -> None:
    rect = layout.hit_regions.get(f"track:{row_index}")
    if rect is None or rect.isEmpty():
        return
    m = layout.metrics
    focused = row_index == state.track_focus
    strength = press_strength if press_key == f"track:{row_index}" else 0.0
    radius = m.radius_sm
    if focused:
        fill = QColor(59, 130, 246, 56)
        border = QColor(ACCENT)
        content_color = QColor(WHITE)
    elif strength > 0:
        fill = QColor.fromRgbF(1, 1, 1, 0.12)
        border = QColor(ACCENT)
        content_color = QColor(WHITE)
    else:
        fill = QColor.fromRgbF(1, 1, 1, 0.08)
        border = QColor.fromRgbF(1, 1, 1, 0.24)
        content_color = TEXT_LIGHT
    painter.setPen(QPen(border, 2 if focused else 1.5))
    painter.setBrush(fill)
    painter.drawRoundedRect(QRectF(rect), radius, radius)
    if strength > 0:
        paint_accent_press_overlay(painter, rect, strength, radius=radius)
        paint_press_overlay(painter, rect, strength, radius=radius)

    if track_row.opens_napi_download:
        icon_kind = _FOOTER_ICONS["download"]
    elif track_row.opens_browse:
        icon_kind = _FOOTER_ICONS["browse"]
    else:
        icon_kind = IconKind.FOLDER

    icon_size = max(20, min(28, rect.height() - 16))
    icon_gap = max(8, m.gap // 2)
    pad_x = max(14, m.track_pad_x // 2)
    font = ui_font(max(14, m.track_font - 4), bold=True)
    fm = QFontMetrics(font)
    text_w = fm.horizontalAdvance(track_row.label)
    content_w = icon_size + icon_gap + text_w
    start_x = rect.x() + max(pad_x, (rect.width() - content_w) // 2)
    icon_y = rect.y() + (rect.height() - icon_size) // 2
    icon_rect = QRect(start_x, icon_y, icon_size, icon_size)
    paint_icon(painter, icon_rect, icon_kind, content_color)
    text_rect = QRect(
        icon_rect.right() + icon_gap,
        rect.y(),
        rect.right() - icon_rect.right() - icon_gap - pad_x,
        rect.height(),
    )
    painter.setFont(font)
    painter.setPen(content_color)
    painter.drawText(
        text_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        track_row.label,
    )


def _paint_footer_status(
    painter: QPainter,
    layout: LayoutSnapshot,
    row_index: int,
    label: str,
) -> None:
    rect = layout.hit_regions.get(f"track:{row_index}")
    if rect is None or rect.isEmpty():
        return
    m = layout.metrics
    font = ui_font(max(12, m.track_font - 4))
    painter.setFont(font)
    painter.setPen(QColor.fromRgbF(1, 1, 1, 0.62))
    painter.drawText(
        rect,
        int(
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignHCenter
            | Qt.TextFlag.TextWordWrap
        ),
        label,
    )


def paint_track_sheet(
    painter: QPainter,
    w: int,
    h: int,
    state: OverlayState,
    layout: LayoutSnapshot,
    *,
    sid: int | None,
    aid: int | None,
    sub_delay: float = 0.0,
    press_key: str | None = None,
    press_strength: float = 0.0,
) -> None:
    m = layout.metrics
    panel_w = layout.panel_w
    panel = QRect(0, 0, panel_w, h)
    painter.fillRect(panel, QColor.fromRgbF(0.08, 0.08, 0.1, 0.96))
    painter.setPen(QPen(QColor.fromRgbF(1, 1, 1, 0.1)))
    painter.drawLine(panel_w, 0, panel_w, h)

    px = m.track_pad_x
    py = m.track_pad_y
    title_font = ui_font(m.track_title_font, bold=True)
    painter.setFont(title_font)
    painter.setPen(QColor(WHITE))
    title = "Subtitles" if state.track_kind == TrackKind.SUBTITLES else "Audio"
    title_h = QFontMetrics(title_font).height()
    title_rect = QRect(px, py, panel_w - px * 2, title_h)
    painter.drawText(
        title_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        title,
    )

    if layout.track_footer_top is not None:
        sep_y = layout.track_footer_top
        painter.setPen(QPen(QColor.fromRgbF(1, 1, 1, 0.14)))
        painter.drawLine(px, sep_y, panel_w - px, sep_y)

    selected = selected_track_index(state, sid, aid)
    rows = state.track_rows or []
    item_font = ui_font(m.track_font)
    item_font_bold = ui_font(m.track_font, bold=True)
    list_clip = None
    if layout.panel_list_bottom > layout.panel_list_top:
        list_clip = QRect(0, layout.panel_list_top, panel_w, layout.panel_list_bottom - layout.panel_list_top)
    if list_clip is not None:
        painter.save()
        painter.setClipRect(list_clip)
    for i, track_row in enumerate(rows):
        if track_row.is_action:
            continue
        rect = layout.hit_regions.get(f"track:{i}")
        if rect is None or rect.isEmpty():
            continue
        on = i == selected
        foc = i == state.track_focus
        action_focused = foc and state.track_action_focus is not None
        row_foc = foc and not action_focused
        strength = press_strength if f"track:{i}" == press_key else 0.0
        label = track_row.label
        if strength > 0:
            paint_accent_press_overlay(painter, rect, strength)
            paint_press_overlay(painter, rect, strength)
            bar = QColor(ACCENT)
            bar.setAlpha(int(255 * strength))
            painter.fillRect(0, rect.y(), m.accent_bar_w, rect.height(), bar)
        elif row_foc:
            painter.fillRect(rect, QColor.fromRgbF(1, 1, 1, 0.14))
            painter.fillRect(0, rect.y(), m.accent_bar_w, rect.height(), QColor(ACCENT))
        elif action_focused:
            painter.fillRect(rect, QColor.fromRgbF(1, 1, 1, 0.08))
            painter.fillRect(
                0,
                rect.y(),
                m.accent_bar_w,
                rect.height(),
                QColor.fromRgbF(1, 1, 1, 0.4),
            )
        elif on:
            painter.fillRect(rect, QColor.fromRgbF(1, 1, 1, 0.08))
            painter.fillRect(
                0,
                rect.y(),
                m.accent_bar_w,
                rect.height(),
                QColor.fromRgbF(1, 1, 1, 0.4),
            )
        draw_font = item_font_bold if on else item_font
        icons_w = 0
        if track_row.show_napi_save or track_row.show_napi_delete:
            save_rect = layout.hit_regions.get(f"track:{i}:save")
            delete_rect = layout.hit_regions.get(f"track:{i}:delete")
            icon_left = min(
                rect.x() + rect.width(),
                *(r.x() for r in (save_rect, delete_rect) if r is not None),
            )
            icons_w = rect.right() - icon_left + m.track_pad_x // 2
        text_rect = rect.adjusted(m.track_pad_x, 0, -(m.track_pad_x + icons_w), 0)
        if on or foc:
            painter.setPen(QColor(WHITE))
        else:
            painter.setPen(QColor.fromRgbF(1, 1, 1, 0.88))
        painter.setFont(draw_font)
        painter.drawText(
            text_rect,
            int(
                Qt.AlignmentFlag.AlignVCenter
                | Qt.AlignmentFlag.AlignLeft
                | Qt.TextFlag.TextWordWrap
            ),
            label,
        )
        _paint_track_action_icons(
            painter,
            state,
            layout,
            i,
            track_row,
            press_key=press_key,
            press_strength=press_strength,
            row_active=on or foc,
        )
    if list_clip is not None:
        painter.restore()

    for i, track_row in enumerate(rows):
        if not track_row.is_action:
            continue
        if track_row.is_sub_delay_control:
            _paint_sub_delay_control(
                painter,
                state,
                layout,
                i,
                sub_delay=sub_delay,
                press_key=press_key,
                press_strength=press_strength,
            )
        elif is_footer_button(track_row):
            _paint_footer_button(
                painter,
                layout,
                i,
                track_row,
                state,
                press_key=press_key,
                press_strength=press_strength,
            )
        else:
            _paint_footer_status(painter, layout, i, track_row.label)
