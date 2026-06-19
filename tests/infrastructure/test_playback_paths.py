"""Playback path candidate tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import PurePosixPath
from unittest.mock import MagicMock

import pytest

from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.infrastructure.smb.playback_paths import (
    directory_path_candidates,
    playback_path_candidates,
    resolve_playback_file,
)


def test_playback_path_candidates_strip_library_root() -> None:
    root = MOCK_LIBRARY_ROOT
    path = MOCK_LIBRARY_ROOT / "12 Angry Men/12 Angry Men.mp4"
    candidates = playback_path_candidates(path, root)
    assert MOCK_LIBRARY_ROOT / "12 Angry Men/12 Angry Men.mp4" in candidates
    assert PurePosixPath("/12 Angry Men/12 Angry Men.mp4") in candidates


def test_playback_path_candidates_add_library_root() -> None:
    root = MOCK_LIBRARY_ROOT
    path = PurePosixPath("/Alien/Alien.mkv")
    candidates = playback_path_candidates(path, root)
    assert PurePosixPath("/Alien/Alien.mkv") in candidates
    assert MOCK_LIBRARY_ROOT / "Alien/Alien.mkv" in candidates


def test_directory_path_candidates_use_parent() -> None:
    root = MOCK_LIBRARY_ROOT
    path = MOCK_LIBRARY_ROOT / "12 Angry Men/12 Angry Men.mp4"
    candidates = directory_path_candidates(path, root)
    assert MOCK_LIBRARY_ROOT / "12 Angry Men" in candidates
    assert PurePosixPath("/12 Angry Men") in candidates


def test_resolve_playback_file_falls_back_to_directory_scan() -> None:
    repo = MagicMock()
    repo.file_size.return_value = None
    repo.list_files_and_directories.return_value = [
        DirectoryEntry(
            name="12 Angry Men.mp4",
            absolute_path=MOCK_LIBRARY_ROOT / "12 Angry Men/12 Angry Men.mp4",
            is_directory=False,
            is_file=True,
        )
    ]

    def file_size(path: PurePosixPath) -> int | None:
        if path == MOCK_LIBRARY_ROOT / "12 Angry Men/12 Angry Men.mp4":
            return 12345
        return None

    repo.file_size.side_effect = file_size

    resolved = resolve_playback_file(
        repo,
        MOCK_LIBRARY_ROOT / "12 Angry Men/wrong-name.mp4",
        MOCK_LIBRARY_ROOT,
        {"mp4"},
    )
    assert resolved == MOCK_LIBRARY_ROOT / "12 Angry Men/12 Angry Men.mp4"


def test_resolve_playback_file_raises_when_unresolved() -> None:
    repo = MagicMock()
    repo.file_size.return_value = None
    repo.list_files_and_directories.return_value = []
    with pytest.raises(FileNotFoundError):
        resolve_playback_file(
            repo,
            MOCK_LIBRARY_ROOT / "Missing/Missing.mp4",
            MOCK_LIBRARY_ROOT,
            {"mp4"},
        )
