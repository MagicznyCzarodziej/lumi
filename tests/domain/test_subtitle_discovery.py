"""Subtitle discovery tests."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.domain.subtitles.discovery import discover_subtitle_files
from lumi.domain.subtitles.file_name_parser import is_subtitle_file
from tests.constants import MOCK_LIBRARY_ROOT


class _FakeLister:
    def __init__(self, entries: dict[PurePosixPath, list[DirectoryEntry]]) -> None:
        self._entries = entries

    def list_files_and_directories(self, directory_absolute_path: PurePosixPath) -> list[DirectoryEntry]:
        return self._entries.get(directory_absolute_path, [])


def test_is_subtitle_file() -> None:
    extensions = {"srt", "ass", "txt"}
    assert is_subtitle_file("Movie.en.srt", extensions)
    assert is_subtitle_file("Movie.ass", extensions)
    assert is_subtitle_file("Movie.txt", extensions)
    assert not is_subtitle_file("Movie.mkv", extensions)


def test_discover_subtitle_files_prefers_matching_basename() -> None:
    directory = MOCK_LIBRARY_ROOT / "Alien"
    video = directory / "Alien.mkv"
    lister = _FakeLister(
        {
            directory: [
                DirectoryEntry(name="Alien.mkv", absolute_path=video, is_directory=False, is_file=True),
                DirectoryEntry(
                    name="Other.srt",
                    absolute_path=directory / "Other.srt",
                    is_directory=False,
                    is_file=True,
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

    paths = discover_subtitle_files(lister, video, {"srt"})

    assert paths == [
        directory / "Alien.en.srt",
        directory / "Other.srt",
    ]


def test_discover_subtitle_files_tries_library_root_path_variants() -> None:
    directory = MOCK_LIBRARY_ROOT / "Alien"
    video = PurePosixPath("/Alien/Alien.mkv")
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

    paths = discover_subtitle_files(
        lister,
        video,
        {"srt"},
        library_root=MOCK_LIBRARY_ROOT,
    )

    assert paths == [directory / "Alien.en.srt"]
