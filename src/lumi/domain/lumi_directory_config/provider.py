"""Per-directory config lookup."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol

from lumi.domain.lumi_directory_config.models import LumiDirectoryConfig


class LumiDirectoryConfigProvider(Protocol):
    def get_lumi_directory_config_for_directory(
        self,
        directory_absolute_path: PurePosixPath,
    ) -> LumiDirectoryConfig | None: ...
