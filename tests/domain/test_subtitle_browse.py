"""Subtitle browse tests."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.domain.subtitles.browse import BrowseEntryKind, build_browse_rows, share_path
from tests.constants import MOCK_LIBRARY_ROOT


class _FakeLister:
    def __init__(self, entries: dict[PurePosixPath, list[DirectoryEntry]]) -> None:
        self._entries = {
            share_path(path): items for path, items in entries.items()
        }

    def list_files_and_directories(self, directory_absolute_path: PurePosixPath) -> list[DirectoryEntry]:
        return self._entries.get(share_path(directory_absolute_path), [])


def test_build_browse_rows_lists_parent_directories_and_subtitles() -> None:
    directory = MOCK_LIBRARY_ROOT / "Alien"
    lister = _FakeLister(
        {
            directory: [
                DirectoryEntry(
                    name="Subs",
                    absolute_path=directory / "Subs",
                    is_directory=True,
                    is_file=False,
                ),
                DirectoryEntry(
                    name="Alien.en.srt",
                    absolute_path=directory / "Alien.en.srt",
                    is_directory=False,
                    is_file=True,
                ),
            ]
        }
    )

    rows, resolved = build_browse_rows(lister, directory, {"srt"})

    assert resolved == share_path(directory)
    assert [row.kind for row in rows] == [
        BrowseEntryKind.PARENT,
        BrowseEntryKind.DIRECTORY,
        BrowseEntryKind.SUBTITLE,
    ]
    assert rows[0].label == ".."
    assert rows[1].label == "Subs/"
    assert rows[2].label == "Alien.en.srt"


def test_build_browse_rows_can_enter_subdirectory() -> None:
    root = MOCK_LIBRARY_ROOT / "Alien"
    sub = root / "Subs"
    lister = _FakeLister(
        {
            root: [
                DirectoryEntry(
                    name="Subs",
                    absolute_path=sub,
                    is_directory=True,
                    is_file=False,
                ),
            ],
            sub: [
                DirectoryEntry(
                    name="Alien.en.srt",
                    absolute_path=sub / "Alien.en.srt",
                    is_directory=False,
                    is_file=True,
                ),
            ],
        }
    )

    outer_rows, _ = build_browse_rows(lister, root, {"srt"})
    sub_row = next(row for row in outer_rows if row.kind == BrowseEntryKind.DIRECTORY)
    inner_rows, inner_resolved = build_browse_rows(lister, sub_row.path, {"srt"})

    assert inner_resolved == share_path(sub)
    assert any(row.kind == BrowseEntryKind.SUBTITLE for row in inner_rows)
