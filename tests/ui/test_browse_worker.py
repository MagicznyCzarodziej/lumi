"""Subtitle browse worker delivery tests."""

from __future__ import annotations

from pathlib import PurePosixPath
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication

from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.domain.subtitles.browse import BrowseEntryKind, share_path
from lumi.ui.player.overlay.deps import OverlayDeps
from lumi.ui.player.overlay.overlay import PlayerOverlay
from lumi.ui.player.overlay.state import View
from tests.constants import MOCK_LIBRARY_ROOT


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeLister:
    def __init__(self, entries: dict[PurePosixPath, list[DirectoryEntry]]) -> None:
        self._entries = {share_path(path): items for path, items in entries.items()}

    def list_files_and_directories(self, directory_absolute_path: PurePosixPath) -> list[DirectoryEntry]:
        return self._entries.get(share_path(directory_absolute_path), [])


def test_browse_lists_files_on_main_thread(qapp) -> None:
    directory = MOCK_LIBRARY_ROOT / "Alien"
    video_path = directory / "Alien.mkv"
    lister = _FakeLister(
        {
            directory: [
                DirectoryEntry(
                    name="Alien.en.srt",
                    absolute_path=directory / "Alien.en.srt",
                    is_directory=False,
                    is_file=True,
                ),
            ]
        }
    )
    controller = MagicMock()
    controller.has_media.return_value = True
    overlay = PlayerOverlay(
        controller,
        OverlayDeps(
            files_lister=lister,
            library_root=MOCK_LIBRARY_ROOT,
            subtitle_extensions=frozenset({"srt"}),
        ),
    )
    overlay.set_media_info("smb://test/video.mkv", video_path)
    overlay.resize(1280, 720)

    overlay.browse.open()
    assert overlay.state.view == View.SUBTITLE_BROWSE

    pool = QThreadPool.globalInstance()
    for _ in range(200):
        qapp.processEvents()
        if overlay.state.browse_rows:
            break
        pool.waitForDone(10)

    assert overlay.state.browse_rows
    assert any(row.kind == BrowseEntryKind.SUBTITLE for row in overlay.state.browse_rows)
