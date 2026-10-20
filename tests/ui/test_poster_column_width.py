"""Poster hero column uses one width everywhere."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QStackedWidget

from lumi.ui.layouts.list_with_poster_layout import ListWithPosterLayout
from lumi.ui.navigation.router import Router
from lumi.ui.screens.library.library_layout import LibraryLayout
from lumi.ui.screens.recently_watched.screen import RecentlyWatchedScreen
from lumi.ui.theme.spacing import POSTER_COLUMN_WIDTH


def test_poster_column_width_matches_across_screens(qtbot) -> None:
    QApplication.instance() or QApplication([])
    library = LibraryLayout()
    list_screen = ListWithPosterLayout()
    recent = RecentlyWatchedScreen(Router(QStackedWidget(), None))  # type: ignore[arg-type]
    for widget in (library, list_screen, recent):
        qtbot.addWidget(widget)
        widget.resize(1_400, 900)
        widget.show()
    qtbot.waitExposed(recent)

    assert library.poster.width() == POSTER_COLUMN_WIDTH
    assert list_screen.poster_widget.width() == POSTER_COLUMN_WIDTH
    assert recent.poster.width() == POSTER_COLUMN_WIDTH
