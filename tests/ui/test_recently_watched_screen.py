"""Recently watched screen navigation tests."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import PurePosixPath

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QApplication, QStackedWidget

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.domain.recent_watch import RecentWatchRecord
from lumi.infrastructure.mock.mock_video_player import MockVideoPlayer
from lumi.infrastructure.poster_cache.disk_poster_cache import DiskPosterCache
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.destinations import (
    LIBRARY,
    RECENTLY_WATCHED,
    Destination,
    EpisodesGroupDestination,
)
from lumi.ui.navigation.navigable_screen import NavigableScreen
from lumi.ui.navigation.router import Router
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.screens.recently_watched.controller import RecentWatchAction
from lumi.ui.screens.recently_watched.screen import RecentlyWatchedScreen
from lumi.ui.theme.spacing import (
    RECENT_WATCH_THUMBNAIL_HEIGHT,
    RECENT_WATCH_THUMBNAIL_WIDTH,
)
from tests.constants import MOCK_LIBRARY_ROOT

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class _LibraryScreen(NavigableScreen):
    def bind(self, destination: Destination, context: ScreenContext) -> None:
        del destination, context


class _RecordingPlayer:
    def __init__(self) -> None:
        self.played: list[PurePosixPath] = []

    def play_video(self, absolute_path: PurePosixPath) -> None:
        self.played.append(absolute_path)


class _WatchHistory:
    def __init__(self, records: list[RecentWatchRecord]) -> None:
        self._records = records

    def resume_position(
        self,
        library_path: PurePosixPath,
        *,
        duration: float | None = None,
    ) -> float | None:
        del library_path, duration
        return None

    def record_playback(
        self,
        library_path: PurePosixPath,
        position: float,
        *,
        duration: float | None = None,
    ) -> None:
        del library_path, position, duration

    def recent_entries(self) -> list[RecentWatchRecord]:
        return self._records


def test_escape_from_recently_watched_returns_to_library(qtbot) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    records = [
        RecentWatchRecord(
            library_path=PurePosixPath("Alien/Alien.mkv"),
            position=120.0,
            duration=7200.0,
            watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
        )
    ]
    context = ScreenContext(
        container.library_repository,
        MockVideoPlayer(),
        _WatchHistory(records),
    )
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(router)
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
    context = ScreenContext(
        container.library_repository,
        MockVideoPlayer(),
        _WatchHistory([]),
    )
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(router)
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
    records = [
        RecentWatchRecord(
            library_path=PurePosixPath("Band of Brothers/Season 1/S01E02.mkv"),
            position=240.0,
            duration=3600.0,
            watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
        )
    ]
    context = ScreenContext(
        container.library_repository,
        MockVideoPlayer(),
        _WatchHistory(records),
    )
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(router)
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
    records = [
        RecentWatchRecord(
            library_path=PurePosixPath("Alien/Alien.mkv"),
            position=120.0,
            duration=7200.0,
            watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
        )
    ]
    context = ScreenContext(
        container.library_repository,
        player,
        _WatchHistory(records),
    )
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(router)
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


def test_recent_row_presents_a_valid_cached_poster_asynchronously(qtbot, tmp_path) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    poster_path = next(
        entry.root_relative_poster_path
        for entry in container.library_repository.get_top_level_entries()
        if entry.name.name == "Alien"
    )
    assert poster_path is not None
    cache = DiskPosterCache(tmp_path)
    cache.write(poster_path, TINY_PNG)
    loader = PosterLoader(container.poster_provider, cache)
    context = ScreenContext(
        container.library_repository,
        MockVideoPlayer(),
        _WatchHistory(
            [
                RecentWatchRecord(
                    library_path=PurePosixPath("Alien/Alien.mkv"),
                    position=120.0,
                    duration=7200.0,
                    watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
                )
            ]
        ),
    )
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(router, poster_loader=loader)
    qtbot.addWidget(screen)
    router.register(type(LIBRARY), _LibraryScreen)
    router.register(type(RECENTLY_WATCHED), lambda: screen)
    router.start(LIBRARY)
    router.push(RECENTLY_WATCHED)

    row = screen.rows.current_row_widget()
    assert row is not None
    qtbot.waitUntil(lambda: row.thumbnail_presentation_state == "loaded")

    assert row.model.poster_path == poster_path
    assert row.thumbnail_size == QSize(
        RECENT_WATCH_THUMBNAIL_WIDTH,
        RECENT_WATCH_THUMBNAIL_HEIGHT,
    )
