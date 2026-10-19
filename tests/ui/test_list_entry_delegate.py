"""List entry delegate sizing tests."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFontMetrics, QImage, QPainter, QStandardItem, QStandardItemModel
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
