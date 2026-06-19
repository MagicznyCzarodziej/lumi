"""LibraryJsonCache round-trip tests."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from lumi.domain.library.models import EntryId, Library, Name, StandaloneFilm
from lumi.infrastructure.library_cache.library_json_cache import LibraryJsonCache


def test_library_json_cache_round_trip(tmp_path: Path) -> None:
    cache_file = tmp_path / "library_cache.json"
    cache = LibraryJsonCache(cache_file)
    library = Library(
        entries=[
            StandaloneFilm(
                id=EntryId("test"),
                name=Name("Test Film"),
                root_relative_path=PurePosixPath("Test Film"),
                root_relative_poster_path=PurePosixPath("Test Film"),
                tags=frozenset({"drama"}),
                franchise=None,
                video_files=[],
            )
        ]
    )

    assert cache.save(library) is True
    loaded = cache.load()

    assert loaded is not None
    assert len(loaded.entries) == 1
    assert loaded.entries[0].id.id == "test"
