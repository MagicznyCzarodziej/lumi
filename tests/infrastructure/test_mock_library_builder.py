"""MockLibraryBuilder and cached mock mode tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import Path, PurePosixPath

from lumi.domain.library.build_progress import LibraryBuildProgress
from lumi.infrastructure.in_memory_cached_library_repository import InMemoryCachedLibraryRepository
from lumi.infrastructure.library_cache.library_json_cache import LibraryJsonCache
from lumi.infrastructure.mock.mock_library_builder import MockLibraryBuilder


def test_mock_library_builder_loads_fixture(tmp_path: Path) -> None:
    builder = MockLibraryBuilder()
    library = builder.build_library_from(MOCK_LIBRARY_ROOT)
    assert len(library.entries) == 66


def test_mock_mode_uses_cache_on_second_initialize(tmp_path: Path) -> None:
    cache_path = tmp_path / "library_cache.json"
    builder = MockLibraryBuilder()
    repository = InMemoryCachedLibraryRepository(builder, LibraryJsonCache(cache_path))
    root = MOCK_LIBRARY_ROOT

    repository.initialize(root)
    first_count = len(repository.get_top_level_entries())
    repository.initialize(root)
    second_count = len(repository.get_top_level_entries())

    assert first_count == 66
    assert second_count == 66
    assert cache_path.is_file()


def test_mock_mode_rebuild_skips_cache(tmp_path: Path, monkeypatch) -> None:
    cache_path = tmp_path / "library_cache.json"
    builder = MockLibraryBuilder()
    repository = InMemoryCachedLibraryRepository(builder, LibraryJsonCache(cache_path))
    root = MOCK_LIBRARY_ROOT
    calls: list[bool] = []

    original_build = builder.build_library_from

    def counting_build(root_library_path: PurePosixPath, progress=None):
        calls.append(True)
        return original_build(root_library_path, progress=progress)

    monkeypatch.setattr(builder, "build_library_from", counting_build)

    repository.initialize(root)
    repository.initialize(root)
    repository.initialize(root, ignore_cache=True)

    assert len(calls) == 2


def test_mock_library_builder_reports_progress() -> None:
    builder = MockLibraryBuilder()
    updates: list[LibraryBuildProgress] = []
    builder.build_library_from(MOCK_LIBRARY_ROOT, progress=updates.append)
    assert updates
    assert updates[-1].completed == updates[-1].total
