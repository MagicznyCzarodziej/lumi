"""Series controller tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import PurePosixPath

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.infrastructure.mock.mock_video_player import MockVideoPlayer
from lumi.ui.components.list_entry import ListEntryTypeKind
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.destinations import EpisodesGroupDestination, SeriesDestination
from lumi.ui.navigation.navigable_screen import NavigableScreen
from lumi.ui.navigation.router import Router
from lumi.ui.screens.series.controller import build_series_state
from PySide6.QtWidgets import QApplication, QStackedWidget


class _StubScreen(NavigableScreen):
    def bind(self, destination: object, context: ScreenContext) -> None:
        del destination, context


def test_build_series_state_from_mock_library() -> None:
    app = QApplication.instance() or QApplication([])
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)

    stack = QStackedWidget()
    context = ScreenContext(
        container.library_repository,
        MockVideoPlayer(),
        container.watch_history,
    )
    router = Router(stack, context)
    router.register(SeriesDestination, _StubScreen)
    router.register(EpisodesGroupDestination, _StubScreen)
    router.start(SeriesDestination(series_id="band-of-brothers"))
    state = build_series_state(
        SeriesDestination(series_id="band-of-brothers"),
        container.library_repository,
        router,
    )

    assert state is not None
    assert state.title == "Band of Brothers"
    assert len(state.entries) == 1
    assert state.entries[0].entry_type.kind is ListEntryTypeKind.PLAYABLES_GROUP
    assert state.entries[0].entry_type.count == 10

    state.entries[0].on_click()
    assert router.current == EpisodesGroupDestination(episodes_group_id="bob-s1")
