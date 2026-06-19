"""SMB-backed per-directory config reader."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import PurePosixPath

from lumi.domain.lumi_directory_config.models import LumiDirectoryConfig
from lumi.domain.lumi_directory_config.provider import LumiDirectoryConfigProvider
from lumi.infrastructure.lumi_directory_config.yaml_file_reader import (
    LUMI_CONFIG_FILE_NAME,
    read_lumi_directory_config,
)
from lumi.infrastructure.smb.smb_file_repository import SmbFileRepository


class SmbLumiDirectoryConfigFileReader(LumiDirectoryConfigProvider):
    def __init__(self, smb_file_repository: SmbFileRepository) -> None:
        self._smb_file_repository = smb_file_repository

    def get_lumi_directory_config_for_directory(
        self,
        directory_absolute_path: PurePosixPath,
    ) -> LumiDirectoryConfig | None:
        config_path = directory_absolute_path / LUMI_CONFIG_FILE_NAME

        def decode(chunks: Iterator[bytes]) -> LumiDirectoryConfig:
            text = b"".join(chunks).decode("utf-8")
            return read_lumi_directory_config(text)

        return self._smb_file_repository.use_read_file_stream(config_path, decode)
