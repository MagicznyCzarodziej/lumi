"""Router navigation tests."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QStackedWidget

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.infrastructure.mock.mock_video_player import MockVideoPlayer
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.destinations import LIBRARY, SeriesDestination
from lumi.ui.navigation.navigable_screen import NavigableScreen
from lumi.ui.navigation.router import Router


class _StubScreen(NavigableScreen):
    def bind(self, destination: object, context: ScreenContext) -> None:
        del destination, context


def test_router_push_and_pop(qtbot) -> None:
    _ = qtbot
    app = QApplication.instance() or QApplication([])
    stack = QStackedWidget()
    container = build_container(Settings(mode="mock"))
    context = ScreenContext(container.library_repository, MockVideoPlayer())
    router = Router(stack, context)
    router.register(type(LIBRARY), lambda: _StubScreen())
    router.register(SeriesDestination, lambda: _StubScreen())

    router.start(LIBRARY)
    assert router.can_pop() is False

    router.push(SeriesDestination(series_id="demo"))
    assert router.can_pop() is True
    assert isinstance(router.current, SeriesDestination)

    assert router.pop() is True
    assert isinstance(router.current, type(LIBRARY))


def test_router_reset_to_clears_detail_history(qtbot) -> None:
    _ = qtbot
    app = QApplication.instance() or QApplication([])
    stack = QStackedWidget()
    container = build_container(Settings(mode="mock"))
    context = ScreenContext(container.library_repository, MockVideoPlayer())
    router = Router(stack, context)
    router.register(type(LIBRARY), lambda: _StubScreen())
    router.register(SeriesDestination, lambda: _StubScreen())

    router.start(LIBRARY)
    router.push(SeriesDestination(series_id="demo"))
    assert router.can_pop() is True

    router.reset_to(LIBRARY)

    assert router.can_pop() is False
    assert isinstance(router.current, type(LIBRARY))
