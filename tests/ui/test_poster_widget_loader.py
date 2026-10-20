"""Shared PosterLoader must not wipe unrelated PosterWidgets."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtWidgets import QApplication

from lumi.infrastructure.poster_cache.disk_poster_cache import DiskPosterCache
from lumi.ui.components.poster_widget import PosterWidget
from lumi.ui.poster_loader import PosterLoader
from tests.ui.test_poster_loader import TINY_PNG, _UnusedPosterProvider, _wait_for_loaded


def test_clearing_hero_poster_does_not_empty_row_thumbnail(tmp_path) -> None:
    QApplication.instance() or QApplication([])
    poster_path = PurePosixPath("Alien")
    disk_cache = DiskPosterCache(tmp_path)
    disk_cache.write(poster_path, TINY_PNG)

    loader = PosterLoader(_UnusedPosterProvider(), disk_cache)
    hero = PosterWidget()
    thumb = PosterWidget()
    hero.bind_loader(loader)
    thumb.bind_loader(loader)
    thumb.set_poster_path(poster_path, immediate=True)
    _wait_for_loaded(loader)

    assert thumb.presentation_state == "loaded"

    hero.set_poster_path(None, immediate=True)

    assert thumb.presentation_state == "loaded"
