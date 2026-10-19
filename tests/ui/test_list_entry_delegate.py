"""List entry delegate sizing tests."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFontMetrics, QImage, QPainter, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem

from lumi.domain.library.models import Name
from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel
from lumi.ui.components.list_entry_delegate.list_entry_delegate import (
    _MARQUEE_SPEED_PX_PER_SECOND,
    _MARQUEE_START_DELAY_MS,
    ListEntryDelegate,
    _marquee_offset,
    _title_font,
)
from lumi.ui.theme.motion import (
    FOCUS_POP_START_SCALE,
    FOCUS_POP_START_SCALE_COMPACT,
    focus_pop_scale,
    focus_pop_scale_compact,
)
from lumi.ui.theme.colors import LIST_SELECTION_ACCENT, LIST_SELECTION_TINT
from lumi.ui.theme.spacing import (
    LIST_ROW_LINE_GAP,
    LIST_ROW_MARGINS,
    LIST_SELECTION_ACCENT_WIDTH,
    LIST_TYPE_INDICATOR_GAP,
    LIST_TYPE_INDICATOR_ICON_SIZE,
)
from lumi.ui.theme.text_metrics import ink_single_line_height


def test_single_line_height_uses_ink_bounds() -> None:
    QApplication.instance() or QApplication([])
    font = _title_font()
    metrics = QFontMetrics(font)
    height = ink_single_line_height(metrics, "gy")
    assert height >= metrics.ascent() + metrics.descent()
    assert height <= metrics.lineSpacing() + 4


def test_long_title_keeps_single_line_row_height_at_narrow_width() -> None:
    QApplication.instance() or QApplication([])
    entries = (
        ListEntryUiModel(
            name=Name(name="Alien", alternative_name="Short alternative title"),
            entry_type=ListEntryType.grouping(1),
        ),
        ListEntryUiModel(
            name=Name(
                name="Lv2 kara Cheat datta Motoyuusha Kouho no Mattari Isekai Life",
                alternative_name="Short alternative title",
            ),
            entry_type=ListEntryType.grouping(1),
        ),
    )
    model = QStandardItemModel()
    for entry in entries:
        item = QStandardItem()
        item.setData(entry, Qt.ItemDataRole.UserRole)
        model.appendRow(item)

    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 540, 100)
    option.state = QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus
    delegate = ListEntryDelegate()

    short_hint = delegate.sizeHint(option, model.index(0, 0))
    long_hint = delegate.sizeHint(option, model.index(1, 0))

    assert long_hint.height() == short_hint.height()


def test_selected_overflowing_title_starts_marquee() -> None:
    QApplication.instance() or QApplication([])
    entry = ListEntryUiModel(
        name=Name(name="Lv2 kara Cheat datta Motoyuusha Kouho no Mattari Isekai Life"),
        entry_type=ListEntryType.grouping(1),
    )
    item = QStandardItem()
    item.setData(entry, Qt.ItemDataRole.UserRole)
    model = QStandardItemModel()
    model.appendRow(item)
    index = model.index(0, 0)

    delegate = ListEntryDelegate()
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 540, delegate.sizeHint(option, index).height())
    option.state = QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus
    image = QImage(option.rect.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)

    delegate.paint(painter, option, index)
    painter.end()

    assert delegate._marquee_timer.isActive()
    delegate._stop_marquee()


def test_selected_row_paints_three_pixel_accent_and_subtle_tint() -> None:
    QApplication.instance() or QApplication([])
    entry = ListEntryUiModel(
        name=Name(name="Alien"),
        entry_type=ListEntryType.grouping(1),
    )
    item = QStandardItem()
    item.setData(entry, Qt.ItemDataRole.UserRole)
    model = QStandardItemModel()
    model.appendRow(item)
    index = model.index(0, 0)

    delegate = ListEntryDelegate()
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 240, delegate.sizeHint(option, index).height())
    option.state = QStyle.StateFlag.State_Selected
    image = QImage(option.rect.size(), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)

    delegate.paint(painter, option, index)
    painter.end()

    center_y = option.rect.height() // 2
    assert image.pixelColor(0, center_y) == QColor(LIST_SELECTION_ACCENT)
    tint = image.pixelColor(LIST_SELECTION_ACCENT_WIDTH + 4, center_y)
    expected_tint = QColor(LIST_SELECTION_TINT)
    assert tint.alpha() == expected_tint.alpha()
    assert abs(tint.red() - expected_tint.red()) <= 8
    assert abs(tint.green() - expected_tint.green()) <= 8
    assert abs(tint.blue() - expected_tint.blue()) <= 8


def test_list_row_uses_shared_a3_spacing_and_indicator_metrics() -> None:
    assert LIST_ROW_MARGINS == (18, 14, 24, 14)
    assert LIST_ROW_LINE_GAP == 6
    assert LIST_TYPE_INDICATOR_ICON_SIZE == 36
    assert LIST_TYPE_INDICATOR_GAP == 10


def test_marquee_waits_before_scrolling() -> None:
    travel_distance = 500

    assert _marquee_offset(_MARQUEE_START_DELAY_MS, travel_distance) == 0
    assert _marquee_offset(_MARQUEE_START_DELAY_MS + 100, travel_distance) > 0


def test_marquee_returns_smoothly_after_reaching_the_end() -> None:
    travel_distance = 500
    forward_duration_ms = (
        travel_distance * 1000 + _MARQUEE_SPEED_PX_PER_SECOND - 1
    ) // _MARQUEE_SPEED_PX_PER_SECOND

    returning_offset = _marquee_offset(
        _MARQUEE_START_DELAY_MS + forward_duration_ms + 1000,
        travel_distance,
    )

    assert travel_distance // 2 < returning_offset < travel_distance


def test_focus_pop_never_scales_beyond_row_bounds() -> None:
    scales = [focus_pop_scale(step / 20) for step in range(21)]

    assert scales[0] == FOCUS_POP_START_SCALE
    assert scales[-1] == 1.0
    assert max(scales) <= 1.0


def test_compact_focus_pop_uses_stronger_start_scale() -> None:
    assert focus_pop_scale_compact(0.0) == FOCUS_POP_START_SCALE_COMPACT
    assert focus_pop_scale_compact(0.0) < focus_pop_scale(0.0)
