"""Cache path isolation between runtime modes."""

from __future__ import annotations

from lumi.config.settings import Settings
from lumi.infrastructure.paths import library_cache_path


def test_mock_and_smb_use_separate_default_library_cache_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "lumi.infrastructure.paths.default_cache_dir",
        lambda: tmp_path,
    )
    smb_path = library_cache_path(Settings(mode="smb"))
    mock_path = library_cache_path(Settings(mode="mock"))
    assert smb_path.name == "library_cache.json"
    assert mock_path.name == "library_cache.mock.json"
    assert smb_path != mock_path
