"""Keyboard activation tests for buttons and list items."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from lumi.ui.components.entries_list import EntriesList
from lumi.ui.components.sidebar import Sidebar
from lumi.ui.components.top_bar import TopBar
from lumi.ui.screens.library.controller import EntriesFilter


def _key(key: Qt.Key, text: str = "") -> QKeyEvent:
    return QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier, text)


def test_top_bar_enter_clicks_filter_button(qtbot) -> None:
    top_bar = TopBar()
    qtbot.addWidget(top_bar)
    top_bar.show()
    qtbot.waitExposed(top_bar)

    received: list[EntriesFilter] = []
    top_bar.filter_changed.connect(received.append)

    button = top_bar._button_order[1]
    button.setFocus()
    qtbot.keyClick(button, Qt.Key.Key_Return)

    assert received == [EntriesFilter.FILMS]


def test_top_bar_space_does_not_click_filter_button(qtbot) -> None:
    top_bar = TopBar()
    qtbot.addWidget(top_bar)
    top_bar.show()
    qtbot.waitExposed(top_bar)

    received: list[EntriesFilter] = []
    top_bar.filter_changed.connect(received.append)

    button = top_bar._button_order[2]
    button.setFocus()
    qtbot.keyClick(button, Qt.Key.Key_Space)

    assert received == []


def test_sidebar_enter_clicks_tag_button(qtbot) -> None:
    host = Sidebar()
    qtbot.addWidget(host)
    host.resize(280, 600)
    host.set_tags(["action", "comedy"])
    host.open_drawer()
    host.show()
    qtbot.waitExposed(host)

    received: list[object] = []
    host.tag_filter_changed.connect(received.append)

    tag_button = host._tag_buttons[1]
    tag_button.setFocus()
    qtbot.keyClick(tag_button, Qt.Key.Key_Enter)

    assert received == ["action"]


def test_entries_list_space_emits_type_to_search() -> None:
    QApplication.instance() or QApplication([])
    entries = EntriesList()
    received: list[str] = []
    entries.type_to_search.connect(received.append)
    entries.set_entries([])

    QApplication.sendEvent(entries, _key(Qt.Key.Key_Space, " "))

    assert received == [" "]


def test_entries_list_space_does_not_activate_row(qtbot) -> None:
    from lumi.domain.library.models import Name
    from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel

    entries = EntriesList()
    qtbot.addWidget(entries)
    clicked: list[int] = []

    model = ListEntryUiModel(
        name=Name(name="Example"),
        entry_type=ListEntryType.single(),
        poster_path=None,
        on_click=lambda: clicked.append(1),
        on_focus=lambda: None,
    )
    entries.set_entries([model])
    entries.show()
    qtbot.waitExposed(entries)
    entries.setFocus()
    entries.setCurrentRow(0)

    qtbot.keyClick(entries, Qt.Key.Key_Space)

    assert clicked == []


def test_entries_list_enter_activates_row(qtbot) -> None:
    from lumi.domain.library.models import Name
    from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel

    entries = EntriesList()
    qtbot.addWidget(entries)
    clicked: list[int] = []

    model = ListEntryUiModel(
        name=Name(name="Example"),
        entry_type=ListEntryType.single(),
        poster_path=None,
        on_click=lambda: clicked.append(1),
        on_focus=lambda: None,
    )
    entries.set_entries([model])
    entries.show()
    qtbot.waitExposed(entries)
    entries.setFocus()
    entries.setCurrentRow(0)

    qtbot.keyClick(entries, Qt.Key.Key_Return)

    assert clicked == [1]
