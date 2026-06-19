"""MockLibraryRepository integration tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import PurePosixPath

from lumi.config.settings import Settings, get_settings
from lumi.container import build_container
from lumi.infrastructure.mock.mock_library_repository import MockLibraryRepository


def test_mock_library_repository_loads_fixture() -> None:
    repository = MockLibraryRepository()
    repository.initialize(MOCK_LIBRARY_ROOT)
    assert len(repository.get_top_level_entries()) == 66


def test_container_mock_mode_loads_library_via_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LUMI_MODE", "mock")
    get_settings.cache_clear()
    settings = Settings(mode="mock", cache_library_json=str(tmp_path / "library_cache.json"))
    container = build_container(settings)
    container.library_repository.initialize(MOCK_LIBRARY_ROOT)
    assert len(container.library_repository.get_top_level_entries()) == 66
    container.library_repository.initialize(MOCK_LIBRARY_ROOT, ignore_cache=True)
    assert len(container.library_repository.get_top_level_entries()) == 66
    get_settings.cache_clear()
