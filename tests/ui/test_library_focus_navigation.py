"""Library screen keyboard focus routing tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStackedWidget

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.infrastructure.mock.mock_video_player import MockVideoPlayer
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.router import Router
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


def test_alphabet_right_moves_focus_to_entries(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.alphabet.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)

    qtbot.keyClick(layout.alphabet, Qt.Key.Key_Right)
    qtbot.wait(10)

    assert screen._entries_has_focus()


def test_entries_up_from_first_row_moves_to_filters(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.entries.scroll_to_row(0)
    layout.entries.setFocus()
    assert layout.entries.focused_row() == 0

    qtbot.keyClick(layout.entries, Qt.Key.Key_Up)

    focus = QApplication.focusWidget()
    assert focus is not None
    assert focus in layout.top_bar._button_order


def test_entries_right_opens_sidebar(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.entries.setFocus()

    qtbot.keyClick(layout.entries, Qt.Key.Key_Right)
    qtbot.wait(10)

    assert layout.sidebar.is_open()
    focus = QApplication.focusWidget()
    assert focus is not None
    assert layout.sidebar.isAncestorOf(focus)


def test_filters_down_moves_focus_to_entries(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.top_bar.focus_first_filter()
    focus = QApplication.focusWidget()
    assert focus is not None
    assert focus in layout.top_bar._button_order

    qtbot.keyClick(focus, Qt.Key.Key_Down)

    assert screen._entries_has_focus()


def test_sidebar_left_and_right_return_to_entries(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    screen._open_sidebar()
    qtbot.wait(10)
    focus = QApplication.focusWidget()
    assert focus is not None
    assert layout.sidebar.isAncestorOf(focus)

    qtbot.keyClick(focus, Qt.Key.Key_Left)
    assert screen._entries_has_focus()
    assert not layout.sidebar.is_open()

    screen._open_sidebar()
    qtbot.wait(10)
    focus = QApplication.focusWidget()
    assert focus is not None

    qtbot.keyClick(focus, Qt.Key.Key_Right)
    assert screen._entries_has_focus()
    assert not layout.sidebar.is_open()


def test_entries_left_focuses_alphabet(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.entries.setFocus()

    qtbot.keyClick(layout.entries, Qt.Key.Key_Left)
    qtbot.wait(10)

    assert screen._alphabet_has_focus()


def test_entries_up_does_not_open_sidebar(qtbot) -> None:
    screen = _library_screen(qtbot)
    layout = screen._layout
    layout.entries.scroll_to_row(0)
    layout.entries.setFocus()

    qtbot.keyClick(layout.entries, Qt.Key.Key_Up)
    qtbot.wait(10)

    assert not layout.sidebar.is_open()

    layout.entries.scroll_to_row(5)
    layout.entries.setFocus()
    qtbot.keyClick(layout.entries, Qt.Key.Key_Up)
    qtbot.wait(10)

    assert not layout.sidebar.is_open()


def test_sidebar_up_from_all_focuses_rebuild(qtbot) -> None:
    screen = _library_screen(qtbot)
    sidebar = screen._layout.sidebar

    screen._open_sidebar()
    qtbot.wait(10)

    all_button = sidebar._tag_buttons[0]
    all_button.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)

    qtbot.keyClick(all_button, Qt.Key.Key_Up)
    qtbot.wait(10)

    focus = QApplication.focusWidget()
    assert focus is sidebar._rebuild_button


def test_sidebar_remembers_last_focused_item(qtbot) -> None:
    screen = _library_screen(qtbot)
    sidebar = screen._layout.sidebar
    assert len(sidebar._tag_buttons) >= 2

    screen._open_sidebar()
    qtbot.wait(10)

    target = sidebar._tag_buttons[1]
    target.setFocus(Qt.FocusReason.OtherFocusReason)
    qtbot.wait(10)

    qtbot.keyClick(target, Qt.Key.Key_Left)
    qtbot.wait(10)
    assert not sidebar.is_open()

    screen._open_sidebar()
    qtbot.wait(10)

    focus = QApplication.focusWidget()
    assert focus is target
