"""Alphabet column scroll zone tests."""

from __future__ import annotations

from PySide6.QtGui import QColor, QImage, QPainter

from lumi.ui.components.alphabet_column import AlphabetColumn
from lumi.ui.theme.colors import ALPHABET_ACTIVE_TINT, BACKGROUND, WHITE
from lumi.ui.theme.spacing import (
    ALPHABET_COLUMN_HEIGHT,
    ALPHABET_COLUMN_WIDTH,
    ALPHABET_FOCUS_RING_WIDTH,
    ALPHABET_LETTER_GAP,
    ALPHABET_LETTER_HEIGHT,
    ALPHABET_LETTER_WIDTH,
)


def test_alphabet_scroll_zones(qtbot) -> None:
    column = AlphabetColumn()
    qtbot.addWidget(column)
    column.set_symbols(["#"] + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    column.show()
    qtbot.waitExposed(column)

    max_scroll = column.scroll_offset_for_index(column.count() - 1)
    assert max_scroll > 0

    first_scroll_row = next(
        row for row in range(column.count()) if column.scroll_offset_for_index(row) > 0
    )
    assert first_scroll_row > 0

    for row in range(first_scroll_row):
        assert column.scroll_offset_for_index(row) == 0, f"row {row} should stay at top"

    last_pinned_row = next(
        row
        for row in range(column.count() - 1, -1, -1)
        if column.scroll_offset_for_index(row) < max_scroll
    )
    assert last_pinned_row < column.count() - 1

    for row in range(last_pinned_row + 1, column.count()):
        assert column.scroll_offset_for_index(row) == max_scroll, f"row {row} should pin to bottom"

    mid_row = (first_scroll_row + last_pinned_row) // 2
    mid_target = column.scroll_offset_for_index(mid_row)
    assert 0 < mid_target < max_scroll, f"mid row {mid_row} should scroll freely"

    column.scroll_to_row(0)
    assert column._scroll_y == 0

    column.scroll_to_row(mid_row)
    assert column._scroll_y == mid_target

    column.scroll_to_row(column.count() - 1)
    assert column._scroll_y == max_scroll


def test_alphabet_uses_compact_a_to_z_rail_metrics() -> None:
    column = AlphabetColumn()
    column.set_symbols(["#"] + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))

    assert (ALPHABET_COLUMN_WIDTH, ALPHABET_LETTER_WIDTH, ALPHABET_LETTER_HEIGHT) == (
        48,
        36,
        34,
    )
    assert ALPHABET_LETTER_GAP == 4
    assert column.width() == ALPHABET_COLUMN_WIDTH
    assert column.height() == ALPHABET_COLUMN_HEIGHT
    assert column.scroll_offset_for_index(column.count() - 1) == (
        column.count() * (ALPHABET_LETTER_HEIGHT + ALPHABET_LETTER_GAP)
        - column.height()
    )


def test_alphabet_active_state_has_a_tint_and_focus_ring(qtbot) -> None:
    column = AlphabetColumn()
    qtbot.addWidget(column)
    column.set_symbols(["A"])
    column.set_active_letter("A")
    column.show()
    qtbot.waitExposed(column)
    column.clearFocus()
    qtbot.wait(0)

    image = column.grab().toImage()
    device_scale = image.devicePixelRatio()
    letter_left = (ALPHABET_COLUMN_WIDTH - ALPHABET_LETTER_WIDTH) // 2
    center_y = ALPHABET_LETTER_HEIGHT // 2

    expected = QImage(1, 1, QImage.Format.Format_ARGB32)
    expected.fill(QColor(BACKGROUND))
    painter = QPainter(expected)
    painter.fillRect(0, 0, 1, 1, QColor(ALPHABET_ACTIVE_TINT))
    painter.end()
    assert image.pixelColor(
        round((letter_left + 1) * device_scale),
        round(center_y * device_scale),
    ) == expected.pixelColor(0, 0)

    column.setFocus()
    qtbot.wait(0)
    focused_image = column.grab().toImage()
    focused_device_scale = focused_image.devicePixelRatio()
    assert focused_image.pixelColor(
        round((letter_left - ALPHABET_FOCUS_RING_WIDTH // 2) * focused_device_scale),
        round(center_y * focused_device_scale),
    ) == QColor(WHITE)


def test_alphabet_keyboard_scroll_is_gradual(qtbot) -> None:
    from PySide6.QtCore import Qt

    column = AlphabetColumn()
    qtbot.addWidget(column)
    column.set_symbols(["#"] + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    column.show()
    qtbot.waitExposed(column)
    column.setFocus()

    max_scroll = column.scroll_offset_for_index(column.count() - 1)
    previous = column._scroll_y

    for step in range(12):
        qtbot.keyClick(column, Qt.Key.Key_Down)
        current = column._scroll_y
        assert current <= max_scroll
        assert current >= previous, f"step {step + 1} scrolled backwards"
        if current == max_scroll:
            break
        previous = current

    assert column._scroll_y < max_scroll


def test_scroll_to_letter_ignored_while_alphabet_focused(qtbot) -> None:
    column = AlphabetColumn()
    qtbot.addWidget(column)
    column.set_symbols(["#"] + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    column.show()
    qtbot.waitExposed(column)
    column.setFocus()

    column.scroll_to_row(2)
    assert column._focused_index == 2
    assert column._scroll_y == 0

    column.scroll_to_letter("Z")
    assert column._focused_index == 2
    assert column._scroll_y == 0

    column.clearFocus()
    column.scroll_to_letter("Z")
    assert column._scroll_y == column.scroll_offset_for_index(column.count() - 1)
