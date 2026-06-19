"""Tests for .lumi directory config YAML reader."""

from __future__ import annotations

import pytest

from lumi.domain.lumi_directory_config.models import LumiDirectoryConfigType
from lumi.infrastructure.lumi_directory_config.yaml_file_reader import read_lumi_directory_config


def test_read_film_series_config() -> None:
    config = read_lumi_directory_config(
        "type: FILM_SERIES\nfranchise: Marvel\ntags:\n  - action\n  - sci-fi\n"
    )
    assert config.type is LumiDirectoryConfigType.FILM_SERIES
    assert config.franchise is not None
    assert config.franchise.name == "Marvel"
    assert config.tags == {"action", "sci-fi"}


def test_read_empty_config() -> None:
    config = read_lumi_directory_config("")
    assert config.type is None
    assert config.franchise is None
    assert config.tags == set()


def test_read_invalid_type_raises() -> None:
    with pytest.raises(KeyError):
        read_lumi_directory_config("type: UNKNOWN\n")
