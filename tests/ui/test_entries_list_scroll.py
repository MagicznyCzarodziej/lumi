"""Entries list scroll offset tests."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from lumi.domain.library.models import Name
from lumi.ui.components.entries_list import EntriesList, _ROWS_FROM_TOP
from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel


def _entry(title: str) -> ListEntryUiModel:
    return ListEntryUiModel(
        name=Name(name=title),
        entry_type=ListEntryType.single(),
        poster_path=None,
        on_click=lambda: None,
        on_focus=lambda: None,
    )


def test_entries_list_keeps_focus_a_few_rows_from_top(qtbot) -> None:
    entries = EntriesList()
    qtbot.addWidget(entries)
    entries.set_entries([_entry(f"Title {index}") for index in range(20)])
    entries.resize(400, 400)
    entries.show()
    qtbot.waitExposed(entries)

    entries.scroll_to_row(0)
    qtbot.wait(10)
    first_rect = entries.visualItemRect(entries.item(0))
    assert first_rect.top() < entries.viewport().height() // 3

    focus_row = 8
    entries.scroll_to_row(focus_row)
    qtbot.wait(10)

    focus_rect = entries.visualItemRect(entries.item(focus_row))
    anchor_rect = entries.visualItemRect(entries.item(focus_row - _ROWS_FROM_TOP))

    assert focus_rect.top() < entries.viewport().height() * 0.6
    assert focus_rect.top() > anchor_rect.top()

    entries.scroll_to_row(15)
    qtbot.wait(10)
    later_rect = entries.visualItemRect(entries.item(15))
    assert later_rect.top() == focus_rect.top()


def test_single_step_navigation_does_not_defer_poster_update(qtbot) -> None:
    QApplication.instance() or QApplication([])
    entries = EntriesList()
    qtbot.addWidget(entries)
    entries.set_entries([_entry(f"Title {index}") for index in range(5)])
    entries.show()
    qtbot.waitExposed(entries)
    entries.setFocus()
    entries.setCurrentRow(0)

    qtbot.keyClick(entries, Qt.Key.Key_Down)

    assert entries.currentRow() == 1
    assert not entries.consume_defer_poster_update()


def test_consume_defer_poster_update_clears_flag(qtbot) -> None:
    QApplication.instance() or QApplication([])
    entries = EntriesList()
    qtbot.addWidget(entries)

    entries._defer_poster_update = True
    assert entries.consume_defer_poster_update()
    assert not entries.consume_defer_poster_update()
