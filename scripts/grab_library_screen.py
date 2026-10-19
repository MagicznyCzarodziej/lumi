"""Grab library home widget PNG for visual comparison (1280×720)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QStackedWidget

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.infrastructure.mock.mock_video_player import MockVideoPlayer
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.router import Router
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.screens.library.screen import LibraryScreen
from lumi.ui.theme import apply_global_theme
from pathlib import PurePosixPath

MOCK_LIBRARY_ROOT = PurePosixPath("/Library")

_OUT = Path(__file__).resolve().parents[1] / ".scratch" / "compare" / "lumi-library-home.png"


def main() -> int:
    app = QApplication(sys.argv)
    apply_global_theme(app)
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    stack = QStackedWidget()
    context = ScreenContext(
        container.library_repository,
        MockVideoPlayer(),
        container.watch_history,
    )
    router = Router(stack, context)
    screen = LibraryScreen(router)
    poster_loader = PosterLoader(
        container.poster_provider,
        container.poster_cache,
        parent=screen,
    )
    screen.bind_poster_loader(poster_loader)
    screen.set_ready(context)
    screen.resize(1280, 720)
    screen.show()
    app.processEvents()
    screen.focus_default()
    for _ in range(120):
        app.processEvents()
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    screen.grab().save(str(_OUT))
    print(_OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
