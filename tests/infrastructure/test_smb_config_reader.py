"""SmbLumiDirectoryConfigFileReader tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT

from pathlib import PurePosixPath

from lumi.domain.lumi_directory_config.models import LumiDirectoryConfigType
from lumi.infrastructure.smb.smb_config_reader import SmbLumiDirectoryConfigFileReader


class _FakeSmbRepo:
    def __init__(self, text: str | None) -> None:
        self._text = text

    def use_read_file_stream(self, absolute_path, block):
        if self._text is None:
            return None
        return block(iter([self._text.encode("utf-8")]))


def test_reads_lumi_config_from_share() -> None:
    reader = SmbLumiDirectoryConfigFileReader(
        _FakeSmbRepo("type: FILM_SERIES\nfranchise: Marvel\ntags: [action]\n")  # type: ignore[arg-type]
    )
    config = reader.get_lumi_directory_config_for_directory(MOCK_LIBRARY_ROOT / "Saga")
    assert config is not None
    assert config.type is LumiDirectoryConfigType.FILM_SERIES
    assert config.franchise is not None
    assert config.franchise.name == "Marvel"


def test_returns_none_when_config_missing() -> None:
    reader = SmbLumiDirectoryConfigFileReader(_FakeSmbRepo(None))  # type: ignore[arg-type]
    assert reader.get_lumi_directory_config_for_directory(MOCK_LIBRARY_ROOT / "Plain") is None
