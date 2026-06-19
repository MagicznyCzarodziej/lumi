"""Keyboard navigation helper tests."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from lumi.domain.library.models import Name
from lumi.ui.components.alphabet_column import AlphabetColumn
from lumi.ui.components.entries_list import EntriesList
from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel


def _key(key: Qt.Key, text: str = "") -> QKeyEvent:
    return QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier, text)


def test_entries_list_letter_emits_type_to_search() -> None:
    QApplication.instance() or QApplication([])
    entries = EntriesList()
    received: list[str] = []
    entries.type_to_search.connect(received.append)
    entries.set_entries(
        [
            ListEntryUiModel(
                name=Name(name="Alien"),
                entry_type=ListEntryType.single(),
                on_click=lambda: None,
                on_focus=lambda: None,
            )
        ]
    )

    QApplication.sendEvent(entries, _key(Qt.Key.Key_A, "a"))

    assert received == ["a"]


def test_alphabet_letter_jumps_without_activating() -> None:
    QApplication.instance() or QApplication([])
    column = AlphabetColumn()
    column.set_symbols(["#", "A", "B", "M", "Z"])
    activated: list[str] = []
    column.letter_activated.connect(activated.append)

    QApplication.sendEvent(column, _key(Qt.Key.Key_M, "m"))

    assert column.currentRow() == column.index_for_letter("M")
    assert activated == []


def test_append_search_character_appends_without_focusing_search_field() -> None:
    from lumi.ui.components.top_bar import TopBar

    QApplication.instance() or QApplication([])
    top_bar = TopBar()
    received: list[str] = []
    top_bar.search_changed.connect(received.append)

    top_bar.append_search_character("a")
    top_bar.append_search_character("b")

    assert received == ["a", "ab"]


def test_set_entries_preserves_focused_entry_not_row_index() -> None:
    QApplication.instance() or QApplication([])
    entries = EntriesList()
    frieren = ListEntryUiModel(
        name=Name(name="Sousou no Frieren"),
        entry_type=ListEntryType.single(),
        on_click=lambda: None,
        on_focus=lambda: None,
    )
    filtered = [
        ListEntryUiModel(
            name=Name(name="Sousou A"),
            entry_type=ListEntryType.single(),
            on_click=lambda: None,
            on_focus=lambda: None,
        ),
        frieren,
        ListEntryUiModel(
            name=Name(name="Sousou B"),
            entry_type=ListEntryType.single(),
            on_click=lambda: None,
            on_focus=lambda: None,
        ),
    ]
    entries.set_entries(filtered)
    entries.scroll_to_row(1)

    full = [
        ListEntryUiModel(
            name=Name(name=f"Title {index}"),
            entry_type=ListEntryType.single(),
            on_click=lambda: None,
            on_focus=lambda: None,
        )
        for index in range(4)
    ] + [frieren] + [
        ListEntryUiModel(
            name=Name(name=f"Title {index}"),
            entry_type=ListEntryType.single(),
            on_click=lambda: None,
            on_focus=lambda: None,
        )
        for index in range(4, 8)
    ]

    entries.set_entries(full, preserve_focus=True)

    assert entries.focused_row() == 4
    assert entries.item(entries.focused_row()).data(Qt.ItemDataRole.UserRole).name.name == "Sousou no Frieren"


def test_entries_list_escape_clears_search_without_back() -> None:
    QApplication.instance() or QApplication([])
    entries = EntriesList(escape_clears_search=True)
    cleared: list[bool] = []
    backspaced: list[bool] = []
    back: list[bool] = []
    entries.clear_search_requested.connect(lambda: cleared.append(True))
    entries.backspace_search_requested.connect(lambda: backspaced.append(True))
    entries.back_requested.connect(lambda: back.append(True))

    QApplication.sendEvent(entries, _key(Qt.Key.Key_Escape))

    assert cleared == [True]
    assert backspaced == []
    assert back == []


def test_entries_list_grave_accent_clears_search_like_escape() -> None:
    QApplication.instance() or QApplication([])
    entries = EntriesList(escape_clears_search=True)
    cleared: list[bool] = []
    entries.clear_search_requested.connect(lambda: cleared.append(True))

    QApplication.sendEvent(entries, _key(Qt.Key.Key_QuoteLeft, "`"))

    assert cleared == [True]


def test_entries_list_backspace_trims_search_without_clearing() -> None:
    QApplication.instance() or QApplication([])
    entries = EntriesList(escape_clears_search=True)
    cleared: list[bool] = []
    backspaced: list[bool] = []
    entries.clear_search_requested.connect(lambda: cleared.append(True))
    entries.backspace_search_requested.connect(lambda: backspaced.append(True))

    QApplication.sendEvent(entries, _key(Qt.Key.Key_Backspace))

    assert backspaced == [True]
    assert cleared == []


def test_empty_entries_list_still_handles_search_backspace() -> None:
    QApplication.instance() or QApplication([])
    entries = EntriesList(escape_clears_search=True)
    backspaced: list[bool] = []
    entries.backspace_search_requested.connect(lambda: backspaced.append(True))
    entries.set_entries([])

    QApplication.sendEvent(entries, _key(Qt.Key.Key_Backspace))

    assert backspaced == [True]


def test_remove_last_search_character_trims_query() -> None:
    from lumi.ui.components.top_bar import TopBar

    QApplication.instance() or QApplication([])
    top_bar = TopBar()
    received: list[str] = []
    top_bar.search_changed.connect(received.append)
    top_bar.append_search_character("s")
    top_bar.append_search_character("o")

    top_bar.remove_last_search_character()

    assert received == ["s", "so", "s"]
