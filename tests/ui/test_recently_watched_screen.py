"""Recently watched screen navigation tests."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import PurePosixPath

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QApplication, QLabel, QStackedWidget

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
from lumi.ui.components.recent_watch_row import RecentWatchRow
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.screens.recently_watched.controller import RecentWatchAction, build_recently_watched_state
from lumi.ui.screens.episodes.screen import EpisodesScreen
from lumi.ui.screens.recently_watched.screen import RecentlyWatchedScreen
from lumi.ui.components.poster_widget import PosterWidget
from lumi.ui.theme.scale import scaled
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
        watched_at = datetime.now(UTC)
        self._records = [
            record
            for record in self._records
            if record.library_path != library_path
        ]
        self._records.append(
            RecentWatchRecord(
                library_path=library_path,
                position=position,
                duration=duration,
                watched_at=watched_at,
            )
        )

    def recent_entries(self) -> list[RecentWatchRecord]:
        return self._records

    def forget_playback(self, library_path: PurePosixPath) -> None:
        self._records = [
            record for record in self._records if record.library_path != library_path
        ]


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


def test_recent_screen_has_library_poster_column(qtbot) -> None:
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
    screen.resize(1200, 800)
    screen.show()
    qtbot.waitExposed(screen)

    main_column = screen.rows.parentWidget()
    assert main_column is not None
    assert screen.poster.width() > 0
    assert screen.poster.geometry().right() < main_column.geometry().left()


def test_selected_recent_row_shows_play_badge(qtbot) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    records = [
        RecentWatchRecord(
            library_path=PurePosixPath("Alien/Alien.mkv"),
            position=120.0,
            duration=7200.0,
            watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
        ),
        RecentWatchRecord(
            library_path=PurePosixPath("Band of Brothers/Season 1/S01E02.mkv"),
            position=240.0,
            duration=3600.0,
            watched_at=datetime(2026, 10, 19, 21, 0, tzinfo=UTC),
        ),
    ]
    context = ScreenContext(
        container.library_repository,
        MockVideoPlayer(),
        _WatchHistory(records),
    )
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(router)
    qtbot.addWidget(screen)
    router.register(type(RECENTLY_WATCHED), lambda: screen)
    router.start(RECENTLY_WATCHED)

    selected = screen.rows.current_row_widget()
    assert selected is not None
    assert selected.play_badge_visible

    screen.rows.setCurrentRow(1)
    first_item = screen.rows.item(0)
    assert first_item is not None
    first_row = screen.rows.itemWidget(first_item)
    assert isinstance(first_row, RecentWatchRow)
    assert not first_row.play_badge_visible
    second_row = screen.rows.current_row_widget()
    assert second_row is not None
    assert second_row.play_badge_visible


def test_recent_row_widget_spans_list_viewport_width(qtbot) -> None:
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
    screen.resize(1200, 800)
    screen.show()
    qtbot.waitExposed(screen)
    state = build_recently_watched_state(
        [
            RecentWatchRecord(
                library_path=PurePosixPath("Alien/Alien.mkv"),
                position=120.0,
                duration=7200.0,
                watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
            )
        ],
        container.library_repository.get_top_level_entries(),
        router,
        MockVideoPlayer(),
    )
    screen.rows.set_rows(state.rows)
    row = screen.rows.current_row_widget()
    assert row is not None
    assert row.width() == screen.rows.viewport().width()


def test_recent_list_scrolls_like_library_entries(qtbot) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT, ignore_cache=True)
    records = [
        RecentWatchRecord(
            library_path=PurePosixPath("Band of Brothers/Season 1/S01E02.mkv"),
            position=240.0,
            duration=3600.0,
            watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
        ),
        RecentWatchRecord(
            library_path=PurePosixPath("Alien/Alien.mkv"),
            position=120.0,
            duration=7200.0,
            watched_at=datetime(2026, 10, 18, 20, 0, tzinfo=UTC),
        ),
    ]
    router = Router(
        QStackedWidget(),
        ScreenContext(container.library_repository, MockVideoPlayer(), _WatchHistory(records)),
    )
    state = build_recently_watched_state(
        records,
        container.library_repository.get_top_level_entries(),
        router,
        MockVideoPlayer(),
    )
    screen = RecentlyWatchedScreen(router)
    qtbot.addWidget(screen)
    screen.resize(scaled(1280), scaled(720))
    screen.show()
    qtbot.waitExposed(screen)
    screen.rows.set_rows(state.rows * 8)

    row_height = screen.rows._row_item_height
    viewport_height = screen.rows.viewport().height()
    assert row_height > 0
    assert viewport_height > 3 * row_height // 2

    screen.rows.setCurrentRow(0)
    qtbot.wait(10)
    first_item = screen.rows.item(0)
    assert first_item is not None
    assert screen.rows.visualItemRect(first_item).top() == 0
    assert screen.rows.verticalScrollBar().value() == 0

    last = screen.rows.entry_count - 1
    screen.rows.setCurrentRow(last)
    qtbot.wait(10)
    item = screen.rows.item(last)
    row_widget = screen.rows.itemWidget(item)
    assert item is not None and row_widget is not None
    viewport = screen.rows.viewport()
    bottom = row_widget.mapTo(viewport, row_widget.rect().bottomRight()).y()
    assert bottom < viewport.height()


def test_recent_row_when_line_combines_date_and_progress_percent(qtbot) -> None:
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
    router.register(type(RECENTLY_WATCHED), lambda: screen)
    router.start(RECENTLY_WATCHED)

    row = screen.rows.current_row_widget()
    assert row is not None
    when = row.findChild(QLabel, "when")
    assert when is not None
    assert when.text().endswith(" · 6%")
    assert when.text().split(" · ", 1)[0] in {"Today", "Yesterday"}


def test_return_from_episodes_restores_recent_row_content(qtbot) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT, ignore_cache=True)
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
    stack = QStackedWidget()
    stack.resize(scaled(1280), scaled(720))
    router = Router(stack, context)
    screen = RecentlyWatchedScreen(router)
    episodes = EpisodesScreen()
    qtbot.addWidget(stack)
    router.register(type(LIBRARY), _LibraryScreen)
    router.register(type(RECENTLY_WATCHED), lambda: screen)
    router.register(EpisodesGroupDestination, lambda: episodes)
    router.start(LIBRARY)
    router.push(RECENTLY_WATCHED)

    row = screen.rows.current_row_widget()
    assert row is not None
    qtbot.keyClick(screen.rows, Qt.Key.Key_Right)
    qtbot.keyClick(screen.rows, Qt.Key.Key_Return)
    assert isinstance(router.current, EpisodesGroupDestination)

    assert router.pop() is True
    qtbot.wait(10)

    row = screen.rows.current_row_widget()
    assert row is not None
    playable = row.findChild(QLabel, "playableName")
    assert playable is not None
    assert playable.text() == "S01E02"
    assert row.width() > 100
    assert row.play_badge_visible


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

    row = screen.rows.current_row_widget()
    assert row is not None
    assert row.model.actions == (
        RecentWatchAction.RESUME,
        RecentWatchAction.REMOVE,
    )
    assert row.selected_action is RecentWatchAction.RESUME

    qtbot.keyClick(screen.rows, Qt.Key.Key_Return)

    assert player.played == [PurePosixPath("Alien/Alien.mkv")]


def test_remove_action_drops_row_from_recently_watched(qtbot) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    history = _WatchHistory(
        [
            RecentWatchRecord(
                library_path=PurePosixPath("Alien/Alien.mkv"),
                position=120.0,
                duration=7200.0,
                watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
            ),
            RecentWatchRecord(
                library_path=PurePosixPath("Band of Brothers/Season 1/S01E02.mkv"),
                position=240.0,
                duration=3600.0,
                watched_at=datetime(2026, 10, 19, 21, 0, tzinfo=UTC),
            ),
        ]
    )
    context = ScreenContext(container.library_repository, MockVideoPlayer(), history)
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(router)
    qtbot.addWidget(screen)
    router.register(type(LIBRARY), _LibraryScreen)
    router.register(type(RECENTLY_WATCHED), lambda: screen)
    router.start(LIBRARY)
    router.push(RECENTLY_WATCHED)

    assert screen.rows.entry_count == 2
    row = screen.rows.current_row_widget()
    assert row is not None
    assert row.model.playable_name == "S01E02"

    qtbot.keyClick(screen.rows, Qt.Key.Key_Right)
    qtbot.keyClick(screen.rows, Qt.Key.Key_Right)
    assert row.selected_action is RecentWatchAction.REMOVE

    qtbot.keyClick(screen.rows, Qt.Key.Key_Return)

    assert screen.rows.entry_count == 1
    row = screen.rows.current_row_widget()
    assert row is not None
    assert row.model.playable_name == "Alien"


def test_reload_refreshes_rows_after_watch_history_changes(qtbot) -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    history = _WatchHistory(
        [
            RecentWatchRecord(
                library_path=PurePosixPath("Alien/Alien.mkv"),
                position=120.0,
                duration=7200.0,
                watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
            )
        ]
    )
    context = ScreenContext(container.library_repository, MockVideoPlayer(), history)
    router = Router(QStackedWidget(), context)
    screen = RecentlyWatchedScreen(router)
    qtbot.addWidget(screen)
    router.register(type(LIBRARY), _LibraryScreen)
    router.register(type(RECENTLY_WATCHED), lambda: screen)
    router.start(LIBRARY)
    router.push(RECENTLY_WATCHED)

    when = screen.rows.current_row_widget()
    assert when is not None
    label = when.findChild(QLabel, "when")
    assert label is not None
    assert label.text().endswith(" · 1%")

    history.record_playback(
        PurePosixPath("Alien/Alien.mkv"),
        3600.0,
        duration=7200.0,
    )
    screen.reload(context)

    label = screen.rows.current_row_widget().findChild(QLabel, "when")  # type: ignore[union-attr]
    assert label is not None
    assert label.text().endswith(" · 50%")


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
