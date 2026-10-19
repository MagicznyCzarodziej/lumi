"""Recently watched screen navigation tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStackedWidget

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.domain.recent_watch import RecentWatchRecord
from lumi.infrastructure.mock.mock_video_player import MockVideoPlayer
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.destinations import (
    LIBRARY,
    RECENTLY_WATCHED,
    Destination,
    EpisodesGroupDestination,
)
from lumi.ui.navigation.navigable_screen import NavigableScreen
from lumi.ui.navigation.router import Router
from lumi.ui.screens.recently_watched.controller import RecentWatchAction
from lumi.ui.screens.recently_watched.screen import RecentlyWatchedScreen
from tests.constants import MOCK_LIBRARY_ROOT


class _LibraryScreen(NavigableScreen):
    def bind(self, destination: Destination, context: ScreenContext) -> None:
        del destination, context


class _RecordingPlayer:
    def __init__(self) -> None:
        self.played: list[PurePosixPath] = []

    def play_video(self, absolute_path: PurePosixPath) -> None:
        self.played.append(absolute_path)


def test_escape_from_recently_watched_returns_to_library(qtbot) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    context = ScreenContext(container.library_repository, MockVideoPlayer())
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(
        router,
        records_loader=lambda: [
            RecentWatchRecord(
                library_path=PurePosixPath("Alien/Alien.mkv"),
                position=120.0,
                duration=7200.0,
                watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
            )
        ],
    )
    qtbot.addWidget(screen)
    router.register(type(LIBRARY), _LibraryScreen)
    router.register(type(RECENTLY_WATCHED), lambda: screen)
    router.start(LIBRARY)
    router.push(RECENTLY_WATCHED)

    assert router.current == RECENTLY_WATCHED

    qtbot.keyClick(screen.rows, Qt.Key.Key_Escape)

    assert router.current == LIBRARY


def test_header_activation_returns_to_library(qtbot) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    context = ScreenContext(container.library_repository, MockVideoPlayer())
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(router, records_loader=lambda: [])
    qtbot.addWidget(screen)
    router.register(type(LIBRARY), _LibraryScreen)
    router.register(type(RECENTLY_WATCHED), lambda: screen)
    router.start(RECENTLY_WATCHED)

    qtbot.keyClick(screen.header, Qt.Key.Key_Return)

    assert router.current == LIBRARY


def test_right_selects_episodes_without_moving_row_then_activates(qtbot) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    context = ScreenContext(container.library_repository, MockVideoPlayer())
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(
        router,
        records_loader=lambda: [
            RecentWatchRecord(
                library_path=PurePosixPath("Band of Brothers/Season 1/S01E02.mkv"),
                position=240.0,
                duration=3600.0,
                watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
            )
        ],
    )
    qtbot.addWidget(screen)
    router.register(type(LIBRARY), _LibraryScreen)
    router.register(type(RECENTLY_WATCHED), lambda: screen)
    router.register(EpisodesGroupDestination, _LibraryScreen)
    router.start(LIBRARY)
    router.push(RECENTLY_WATCHED)

    qtbot.keyClick(screen.rows, Qt.Key.Key_Right)

    row = screen.rows.current_row_widget()
    assert row is not None
    assert screen.rows.currentRow() == 0
    assert row.selected_action is RecentWatchAction.EPISODES

    qtbot.keyClick(screen.rows, Qt.Key.Key_Return)

    assert router.current == EpisodesGroupDestination(episodes_group_id="bob-s1")


def test_standalone_film_exposes_resume_only_and_plays_that_file(qtbot) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    player = _RecordingPlayer()
    context = ScreenContext(container.library_repository, player)
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(
        router,
        records_loader=lambda: [
            RecentWatchRecord(
                library_path=PurePosixPath("Alien/Alien.mkv"),
                position=120.0,
                duration=7200.0,
                watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
            )
        ],
    )
    qtbot.addWidget(screen)
    router.register(type(LIBRARY), _LibraryScreen)
    router.register(type(RECENTLY_WATCHED), lambda: screen)
    router.start(LIBRARY)
    router.push(RECENTLY_WATCHED)

    qtbot.keyClick(screen.rows, Qt.Key.Key_Right)
    row = screen.rows.current_row_widget()
    assert row is not None
    assert row.selected_action is RecentWatchAction.RESUME

    qtbot.keyClick(screen.rows, Qt.Key.Key_Return)

    assert player.played == [PurePosixPath("Alien/Alien.mkv")]
