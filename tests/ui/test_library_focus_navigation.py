"""Library screen keyboard focus routing tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QStackedWidget

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.ui.components.inline_tag_ribbon import InlineTagRibbon
from lumi.infrastructure.mock.mock_video_player import MockVideoPlayer
from lumi.ui.components.list_entry_delegate import ListEntryDelegate
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.router import Router
from lumi.ui.screens.library.controller import EntriesFilter
from lumi.ui.screens.library.screen import LibraryScreen


def _library_screen(qtbot) -> LibraryScreen:
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    stack = QStackedWidget()
    context = ScreenContext(container.library_repository, MockVideoPlayer())
    router = Router(stack, context)
    screen = LibraryScreen(router)
    qtbot.addWidget(screen)
    screen.set_ready(context)
    screen.resize(1280, 720)
    screen.show()
    screen.activateWindow()
    qtbot.waitExposed(screen)
    return screen


def _focus_entries(qtbot, screen: LibraryScreen) -> None:
    screen.activateWindow()
    screen._layout.entries.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.waitUntil(screen._entries_has_focus)


def test_alphabet_right_moves_focus_to_entries(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.alphabet.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)

    qtbot.keyClick(layout.alphabet, Qt.Key.Key_Right)
    qtbot.wait(10)

    assert screen._entries_has_focus()
    delegate = layout.entries.itemDelegate()
    assert isinstance(delegate, ListEntryDelegate)
    assert delegate._pop_timer.isActive()
    qtbot.wait(300)
    assert delegate._pop_timer.isActive()


def test_entries_up_from_first_row_moves_to_tag_ribbon(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.entries.scroll_to_row(0)
    layout.entries.setFocus()
    assert layout.entries.focused_row() == 0

    qtbot.keyClick(layout.entries, Qt.Key.Key_Up)

    focus = QApplication.focusWidget()
    assert focus is not None
    assert focus.parent() is layout.top_bar.findChild(InlineTagRibbon)


def test_top_chrome_routes_from_recent_through_rebuild(qtbot) -> None:
    screen = _library_screen(qtbot)
    top_bar = screen._layout.top_bar
    search = top_bar.findChild(QLineEdit, "searchField")
    assert search is not None

    chrome = [
        top_bar._recent_button,
        search,
        top_bar._buttons[EntriesFilter.ALL],
        top_bar._buttons[EntriesFilter.FILMS],
        top_bar._buttons[EntriesFilter.SERIES],
        top_bar._rebuild_button,
    ]
    chrome[0].setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)
    assert QApplication.focusWidget() is chrome[0]

    for current, expected in zip(chrome, chrome[1:], strict=False):
        qtbot.keyClick(current, Qt.Key.Key_Right)
        qtbot.wait(10)
        assert QApplication.focusWidget() is expected

    for current, expected in zip(reversed(chrome), reversed(chrome[:-1]), strict=False):
        qtbot.keyClick(current, Qt.Key.Key_Left)
        qtbot.wait(10)
        assert QApplication.focusWidget() is expected


def test_recent_button_exposes_screen_activation_seam(qtbot) -> None:
    screen = _library_screen(qtbot)
    requested: list[bool] = []
    screen.recent_requested.connect(lambda: requested.append(True))

    recent = screen._layout.top_bar._recent_button
    recent.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.keyClick(recent, Qt.Key.Key_Return)

    assert requested == [True]


def test_chrome_tag_ribbon_and_entries_form_a_vertical_focus_path(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    ribbon = layout.top_bar.findChild(InlineTagRibbon)
    assert ribbon is not None
    all_tags = next(button for button in ribbon.findChildren(QPushButton) if button.text() == "All")

    layout.top_bar._rebuild_button.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)
    qtbot.keyClick(layout.top_bar._rebuild_button, Qt.Key.Key_Down)
    qtbot.wait(10)
    assert QApplication.focusWidget() is all_tags

    qtbot.keyClick(all_tags, Qt.Key.Key_Down)
    qtbot.wait(10)
    assert screen._entries_has_focus()

    layout.entries.scroll_to_row(0)
    qtbot.keyClick(layout.entries, Qt.Key.Key_Up)
    qtbot.wait(10)
    assert QApplication.focusWidget() is all_tags

    qtbot.keyClick(all_tags, Qt.Key.Key_Up)
    qtbot.wait(10)
    assert QApplication.focusWidget() is layout.top_bar._rebuild_button


def test_entries_right_keeps_focus_on_entries(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.entries.setFocus()
    qtbot.wait(10)

    qtbot.keyClick(layout.entries, Qt.Key.Key_Right)
    qtbot.wait(10)

    assert screen._entries_has_focus()


def test_library_shell_places_full_height_alphabet_rail_between_poster_and_content(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout

    assert layout.poster.geometry().right() < layout.alphabet_rail.geometry().left()
    assert layout.alphabet_rail.geometry().right() < layout.main_content.geometry().left()
    assert layout.alphabet_rail.height() == layout.main_content.height()
    assert layout.alphabet.parentWidget() is layout.alphabet_rail
    assert not hasattr(layout, "sidebar")


def test_filters_down_moves_focus_to_tag_ribbon(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.top_bar.focus_first_filter()
    focus = QApplication.focusWidget()
    assert focus is not None
    assert focus in layout.top_bar._button_order

    qtbot.keyClick(focus, Qt.Key.Key_Down)

    focus = QApplication.focusWidget()
    assert focus is not None
    assert focus.parent() is layout.top_bar.findChild(InlineTagRibbon)


def test_inline_tag_ribbon_composes_with_search_and_type_filters(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    ribbon = layout.top_bar.findChild(InlineTagRibbon)
    assert ribbon is not None

    qtbot.mouseClick(layout.top_bar._buttons[EntriesFilter.FILMS], Qt.MouseButton.LeftButton)
    search = layout.top_bar.findChild(QLineEdit, "searchField")
    assert search is not None
    search.setText("alien")

    sci_fi = next(
        button
        for button in ribbon.findChildren(QPushButton)
        if button.text() == "Sci-fi"
    )
    qtbot.mouseClick(sci_fi, Qt.MouseButton.LeftButton)

    titles = [
        layout.entries.item(index).data(Qt.ItemDataRole.UserRole).name.name
        for index in range(layout.entries.count())
    ]
    assert screen._entries_filter is EntriesFilter.FILMS
    assert screen._search_query == "alien"
    assert screen._tag_filter == "sci-fi"
    assert titles == ["Alien"]


def test_typing_from_entries_searches_and_escape_restores_entries(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    unfiltered_count = layout.entries.count()
    _focus_entries(qtbot, screen)

    qtbot.keyClicks(layout.entries, "alien")
    qtbot.wait(10)

    assert screen._search_query == "alien"
    assert layout.entries.count() == 1
    assert screen._entries_has_focus()

    qtbot.keyClick(layout.entries, Qt.Key.Key_Escape)
    qtbot.wait(10)

    assert screen._search_query == ""
    assert layout.entries.count() == unfiltered_count
    assert screen._entries_has_focus()


def test_entry_selection_synchronizes_alphabet_and_poster(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    alien_row = next(
        index
        for index in range(layout.entries.count())
        if layout.entries.item(index).data(Qt.ItemDataRole.UserRole).name.name == "Alien"
    )
    layout.entries.setFocus(Qt.FocusReason.OtherFocusReason)

    layout.entries.scroll_to_row(alien_row)

    selected = layout.entries.item(alien_row).data(Qt.ItemDataRole.UserRole)
    assert layout.entries.currentRow() == alien_row
    assert layout.alphabet._active_letter == "A"
    assert layout.poster._current_path == selected.poster_path


def test_entries_left_focuses_alphabet(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    _focus_entries(qtbot, screen)

    qtbot.keyClick(layout.entries, Qt.Key.Key_Left)
    qtbot.wait(10)

    assert screen._alphabet_has_focus()
    assert layout.alphabet._pop_timer.isActive()
    qtbot.wait(300)
    assert layout.alphabet._pop_timer.isActive()


def test_entries_up_from_later_rows_keeps_entries_focus(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.entries.scroll_to_row(5)
    _focus_entries(qtbot, screen)

    qtbot.keyClick(layout.entries, Qt.Key.Key_Up)
    qtbot.wait(10)

    assert screen._entries_has_focus()
    assert layout.entries.focused_row() == 4
