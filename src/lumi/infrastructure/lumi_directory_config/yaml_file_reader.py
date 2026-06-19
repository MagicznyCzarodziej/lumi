"""Per-directory .lumi YAML config reader."""

from __future__ import annotations

from dataclasses import dataclass

from lumi.domain.library.models import Franchise
from lumi.domain.lumi_directory_config.models import LumiDirectoryConfig, LumiDirectoryConfigType
from lumi.infrastructure.yaml_file_reader import read_yaml_mapping

LUMI_CONFIG_FILE_NAME = ".lumi"


@dataclass(frozen=True)
class LumiDirectoryConfigRaw:
    type: str | None = None
    franchise: str | None = None
    tags: list[str] | None = None


def read_lumi_directory_config(text: str) -> LumiDirectoryConfig:
    raw = read_yaml_mapping(text)
    config = LumiDirectoryConfigRaw(
        type=raw.get("type"),
        franchise=raw.get("franchise"),
        tags=raw.get("tags"),
    )
    config_type = None
    if config.type is not None:
        config_type = LumiDirectoryConfigType[config.type]
    franchise = Franchise(config.franchise) if config.franchise else None
    tags = set(config.tags or [])
    return LumiDirectoryConfig(type=config_type, franchise=franchise, tags=tags)
