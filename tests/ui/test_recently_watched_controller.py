"""Recently watched screen state tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath

from PySide6.QtWidgets import QApplication, QStackedWidget

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.domain.recent_watch import RecentWatchRecord
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.router import Router
from lumi.ui.screens.recently_watched.controller import (
    RecentWatchAction,
    build_recently_watched_state,
)
from tests.constants import MOCK_LIBRARY_ROOT


class _RecordingPlayer:
    def __init__(self) -> None:
        self.played: list[PurePosixPath] = []

    def play_video(self, absolute_path: PurePosixPath) -> None:
        self.played.append(absolute_path)


def test_state_orders_resolved_records_and_resumes_selected_item() -> None:
    QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    player = _RecordingPlayer()
    router = Router(
        QStackedWidget(),
        ScreenContext(container.library_repository, player),
    )
    records = [
        RecentWatchRecord(
            library_path=PurePosixPath("Alien/Alien.mkv"),
            position=120.0,
            duration=7200.0,
            watched_at=datetime(2026, 10, 18, 19, 0, tzinfo=UTC),
        ),
        RecentWatchRecord(
            library_path=PurePosixPath("Band of Brothers/Season 1/S01E02.mkv"),
            position=240.0,
            duration=3600.0,
            watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
        ),
    ]

    state = build_recently_watched_state(
        records,
        container.library_repository.get_top_level_entries(),
        router,
        player,
    )

    assert [(row.playable_name, row.show_name) for row in state.rows] == [
        ("S01E02", "Band of Brothers"),
        ("Alien", None),
    ]
    assert state.rows[0].actions == (
        RecentWatchAction.RESUME,
        RecentWatchAction.EPISODES,
    )
    assert state.rows[1].actions == (RecentWatchAction.RESUME,)

    state.rows[0].activate(RecentWatchAction.RESUME)

    assert player.played == [PurePosixPath("Band of Brothers/Season 1/S01E02.mkv")]
