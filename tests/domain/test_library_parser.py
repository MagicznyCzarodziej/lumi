"""LibraryParser integration tests — one fixture directory per strategy type."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT

from pathlib import PurePosixPath

from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.domain.library.building.library_parser import LibraryParser
from lumi.domain.library.models import FilmSeries, MediaGrouping, Series, StandaloneFilm
from lumi.domain.lumi_directory_config.models import LumiDirectoryConfig, LumiDirectoryConfigType
from lumi.domain.lumi_directory_config.provider import LumiDirectoryConfigProvider
from lumi.domain.poster.image_file_poster_provider import ImageFilePosterProvider
from tests.in_memory_files import InMemoryFileTree


class _StaticConfigProvider(LumiDirectoryConfigProvider):
    def __init__(self, configs: dict[PurePosixPath, LumiDirectoryConfig]) -> None:
        self._configs = configs

    def get_lumi_directory_config_for_directory(
        self,
        directory_absolute_path: PurePosixPath,
    ) -> LumiDirectoryConfig | None:
        return self._configs.get(directory_absolute_path)


def _parser(
    tree: InMemoryFileTree,
    *,
    configs: dict[PurePosixPath, LumiDirectoryConfig] | None = None,
) -> LibraryParser:
    provider = ImageFilePosterProvider(
        file_repository=tree,
        files_lister=tree,
        poster_file_name="poster",
        supported_file_extensions={".jpg"},
    )
    return LibraryParser(
        file_lister=tree,
        poster_provider=provider,
        video_extensions={"mkv"},
        lumi_directory_config_provider=_StaticConfigProvider(configs or {}),
    )


def _directory(name: str, path: PurePosixPath) -> DirectoryEntry:
    return DirectoryEntry(name=name, absolute_path=path, is_directory=True, is_file=False)


def test_parse_standalone_film_directory() -> None:
    root = MOCK_LIBRARY_ROOT / "Alien"
    tree = InMemoryFileTree()
    tree.add_directory(root)
    tree.add_file(root / "Alien.mkv")

    entry = _parser(tree).parse_directory(_directory("Alien", root))

    assert isinstance(entry, StandaloneFilm)
    assert entry.name.name == "Alien"
    assert len(entry.video_files) == 1
    assert entry.video_files[0].name.name == "Alien.mkv"


def test_parse_film_series_directory() -> None:
    root = MOCK_LIBRARY_ROOT / "Marvel"
    film_one = root / "[1] Iron Man"
    tree = InMemoryFileTree()
    tree.add_directory(root)
    tree.add_directory(film_one)
    tree.add_file(film_one / "Iron Man.mkv")
    configs = {
        root: LumiDirectoryConfig(type=LumiDirectoryConfigType.FILM_SERIES, franchise=None, tags={"action"}),
    }

    entry = _parser(tree, configs=configs).parse_directory(_directory("Marvel", root))

    assert isinstance(entry, FilmSeries)
    assert entry.name.name == "Marvel"
    assert len(entry.films) == 1
    assert entry.films[0].name.name == "Iron Man"
    assert entry.tags == frozenset({"action"})


def test_parse_series_directory() -> None:
    root = MOCK_LIBRARY_ROOT / "Breaking Bad"
    season = root / "Season 01"
    tree = InMemoryFileTree()
    tree.add_directory(root)
    tree.add_directory(season)
    tree.add_file(season / "Breaking Bad - S01E01 - Pilot.mkv")
    tree.add_file(season / "Breaking Bad - S01E02 - Cat's in the Bag.mkv")

    entry = _parser(tree).parse_directory(_directory("Breaking Bad", root))

    assert isinstance(entry, Series)
    assert entry.name.name == "Breaking Bad"
    assert len(entry.seasons) == 1
    assert len(entry.seasons[0].episodes) == 2


def test_parse_series_directory_sorts_bracketed_seasons_by_number() -> None:
    root = MOCK_LIBRARY_ROOT / "Anime"
    season_eleven = root / "[11] Season Eleven"
    season_one = root / "[01] Season One"
    tree = InMemoryFileTree()
    tree.add_directory(root)
    tree.add_directory(season_eleven)
    tree.add_directory(season_one)
    tree.add_file(season_eleven / "Anime - S11E01 - Start.mkv")
    tree.add_file(season_one / "Anime - S01E01 - Start.mkv")

    entry = _parser(tree).parse_directory(_directory("Anime", root))

    assert isinstance(entry, Series)
    assert [season.name.name for season in entry.seasons] == [
        "[01] Season One",
        "[11] Season Eleven",
    ]


def test_parse_media_grouping_directory() -> None:
    root = MOCK_LIBRARY_ROOT / "Shared Universe"
    film = root / "[1] Solo Film"
    season = root / "Season 01"
    tree = InMemoryFileTree()
    tree.add_directory(root)
    tree.add_directory(film)
    tree.add_directory(season)
    tree.add_file(film / "Solo Film.mkv")
    tree.add_file(season / "Shared Universe - S01E01 - Pilot.mkv")

    entry = _parser(tree).parse_directory(_directory("Shared Universe", root))

    assert isinstance(entry, MediaGrouping)
    assert entry.name.name == "Shared Universe"
    assert len(entry.entries) == 2


def test_parse_directory_with_no_matching_strategy_returns_none() -> None:
    root = MOCK_LIBRARY_ROOT / "Empty"
    tree = InMemoryFileTree()
    tree.add_directory(root)

    assert _parser(tree).parse_directory(_directory("Empty", root)) is None


def test_mock_library_json_entry_count_matches_fixture() -> None:
    from lumi.domain.library.serialization.from_json import library_from_json
    from lumi.infrastructure.mock.mock_library_builder import DEFAULT_FIXTURE_PATH

    text = DEFAULT_FIXTURE_PATH.read_text(encoding="utf-8")
    library = library_from_json(text)
    assert len(library.entries) == 66
