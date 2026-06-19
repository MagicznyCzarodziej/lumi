"""SmbLibraryBuilder tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT

from pathlib import PurePosixPath
from unittest.mock import MagicMock

from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.domain.library.models import EntryId, LibraryEntry, Name, StandaloneFilm
from lumi.infrastructure.smb.smb_library_builder import SmbLibraryBuilder


def _film(name: str) -> StandaloneFilm:
    return StandaloneFilm(
        id=EntryId(name.lower()),
        name=Name(name),
        root_relative_path=PurePosixPath(name),
        root_relative_poster_path=PurePosixPath(name),
        tags=frozenset(),
        franchise=None,
        video_files=[],
    )


def test_build_library_from_parses_each_subdirectory() -> None:
    repo = MagicMock()
    parser = MagicMock()
    root = MOCK_LIBRARY_ROOT
    dirs = [
        DirectoryEntry("Alpha", MOCK_LIBRARY_ROOT / "Alpha", True, False),
        DirectoryEntry("Beta", MOCK_LIBRARY_ROOT / "Beta", True, False),
    ]
    repo.list_files_and_directories.return_value = dirs
    parser.parse_directory.side_effect = [_film("Alpha"), _film("Beta")]

    library = SmbLibraryBuilder(repo, parser).build_library_from(root)

    assert [entry.name.name for entry in library.entries] == ["Alpha", "Beta"]
    repo.list_files_and_directories.assert_called_once_with(root)
    assert parser.parse_directory.call_count == 2


def test_build_library_from_reports_progress() -> None:
    repo = MagicMock()
    parser = MagicMock()
    root = MOCK_LIBRARY_ROOT
    dirs = [
        DirectoryEntry("Alpha", MOCK_LIBRARY_ROOT / "Alpha", True, False),
        DirectoryEntry("Beta", MOCK_LIBRARY_ROOT / "Beta", True, False),
    ]
    repo.list_files_and_directories.return_value = dirs
    parser.parse_directory.side_effect = [_film("Alpha"), _film("Beta")]
    updates: list = []

    SmbLibraryBuilder(repo, parser).build_library_from(root, progress=updates.append)

    assert updates
    assert updates[0].completed == 0
    assert updates[-1].completed == updates[-1].total == 2
