"""Mock directory config — always returns None."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.lumi_directory_config.models import LumiDirectoryConfig
from lumi.domain.lumi_directory_config.provider import LumiDirectoryConfigProvider


class MockLumiDirectoryConfigProvider(LumiDirectoryConfigProvider):
    def get_lumi_directory_config_for_directory(
        self,
        directory_absolute_path: PurePosixPath,
    ) -> LumiDirectoryConfig | None:
        return None
