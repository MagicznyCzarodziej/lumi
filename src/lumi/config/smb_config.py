"""SMB connection settings — infra consumes this, not the full Settings bag."""

from __future__ import annotations

from dataclasses import dataclass

from lumi.config.settings import Settings


@dataclass(frozen=True)
class SmbConfig:
    hostname: str
    share_name: str
    domain: str
    username: str
    password: str

    @classmethod
    def from_settings(cls, settings: Settings) -> SmbConfig:
        return cls(
            hostname=str(settings.smb_hostname),
            share_name=str(settings.smb_share_name),
            domain=str(settings.smb_domain),
            username=str(settings.smb_username),
            password=str(settings.smb_password),
        )
