"""InMemoryCachedLibraryRepository tests."""

from __future__ import annotations

from pathlib import PurePosixPath
from unittest.mock import MagicMock

import pytest

from lumi.domain.library.models import EntryId, Library, Name, StandaloneFilm
from lumi.infrastructure.in_memory_cached_library_repository import InMemoryCachedLibraryRepository

ROOT_PATH = PurePosixPath("/library")


def _film(name: str) -> StandaloneFilm:
    return StandaloneFilm(
        id=EntryId(name.lower().replace(" ", "-")),
        name=Name(name),
        root_relative_path=PurePosixPath(name),
        root_relative_poster_path=PurePosixPath(name),
        tags=frozenset(),
        franchise=None,
        video_files=[],
    )


@pytest.fixture
def library_builder() -> MagicMock:
    return MagicMock()


@pytest.fixture
def library_cache() -> MagicMock:
    cache = MagicMock()
    cache.save = MagicMock()
    return cache


@pytest.fixture
def repository(library_builder: MagicMock, library_cache: MagicMock) -> InMemoryCachedLibraryRepository:
    return InMemoryCachedLibraryRepository(library_builder, library_cache)


class TestSorting:
    def test_should_sort_entries_by_name_ignoring_articles(
        self,
        repository: InMemoryCachedLibraryRepository,
        library_builder: MagicMock,
        library_cache: MagicMock,
    ) -> None:
        unsorted = [
            _film("Inception"),
            _film("Avatar"),
            _film("A Beautiful Mind"),
            _film("Zodiac"),
            _film("The Abyss"),
            _film("An Officer and a Gentleman"),
        ]
        library_cache.load.return_value = None
        library_builder.build_library_from.return_value = Library(entries=unsorted)

        repository.initialize(ROOT_PATH)

        assert [entry.name.name for entry in repository.get_top_level_entries()] == [
            "The Abyss",
            "Avatar",
            "A Beautiful Mind",
            "Inception",
            "An Officer and a Gentleman",
            "Zodiac",
        ]

    def test_should_save_sorted_entries_to_cache(
        self,
        repository: InMemoryCachedLibraryRepository,
        library_builder: MagicMock,
        library_cache: MagicMock,
    ) -> None:
        unsorted = [_film("Zodiac"), _film("Avatar"), _film("The Matrix")]
        library_cache.load.return_value = None
        library_builder.build_library_from.return_value = Library(entries=unsorted)

        repository.initialize(ROOT_PATH)

        saved_library: Library = library_cache.save.call_args[0][0]
        assert [entry.name.name for entry in saved_library.entries] == [
            "Avatar",
            "The Matrix",
            "Zodiac",
        ]

    def test_should_not_re_sort_when_loading_from_cache(
        self,
        repository: InMemoryCachedLibraryRepository,
        library_builder: MagicMock,
        library_cache: MagicMock,
    ) -> None:
        cached = [_film("Zodiac"), _film("Avatar"), _film("The Matrix")]
        library_cache.load.return_value = Library(entries=cached)

        repository.initialize(ROOT_PATH)

        assert [entry.name.name for entry in repository.get_top_level_entries()] == [
            "Zodiac",
            "Avatar",
            "The Matrix",
        ]


class TestCaching:
    def test_should_use_cache_when_available(
        self,
        repository: InMemoryCachedLibraryRepository,
        library_builder: MagicMock,
        library_cache: MagicMock,
    ) -> None:
        library_cache.load.return_value = Library(entries=[_film("Cached Film")])

        repository.initialize(ROOT_PATH)

        assert [entry.name.name for entry in repository.get_top_level_entries()] == ["Cached Film"]
        library_builder.build_library_from.assert_not_called()

    def test_should_build_from_builder_when_cache_is_empty(
        self,
        repository: InMemoryCachedLibraryRepository,
        library_builder: MagicMock,
        library_cache: MagicMock,
    ) -> None:
        library_cache.load.return_value = None
        library_builder.build_library_from.return_value = Library(entries=[_film("Built Film")])

        repository.initialize(ROOT_PATH)

        assert [entry.name.name for entry in repository.get_top_level_entries()] == ["Built Film"]
        library_builder.build_library_from.assert_called_once_with(ROOT_PATH, progress=None)
        library_cache.save.assert_called_once()

    def test_should_record_cache_warning_when_save_fails(
        self,
        repository: InMemoryCachedLibraryRepository,
        library_builder: MagicMock,
        library_cache: MagicMock,
    ) -> None:
        library_cache.load.return_value = None
        library_cache.save.return_value = False
        library_builder.build_library_from.return_value = Library(entries=[_film("Built Film")])

        repository.initialize(ROOT_PATH)

        assert repository.last_cache_warning == "Could not save library cache to disk."

    def test_should_skip_cache_when_ignore_cache_is_true(
        self,
        repository: InMemoryCachedLibraryRepository,
        library_builder: MagicMock,
        library_cache: MagicMock,
    ) -> None:
        library_builder.build_library_from.return_value = Library(entries=[_film("Fresh Film")])

        repository.initialize(ROOT_PATH, ignore_cache=True)

        assert [entry.name.name for entry in repository.get_top_level_entries()] == ["Fresh Film"]
        library_cache.load.assert_not_called()
        library_builder.build_library_from.assert_called_once_with(ROOT_PATH, progress=None)
