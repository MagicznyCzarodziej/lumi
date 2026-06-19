"""playback_uri tests."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.config.settings import Settings
from lumi.config.smb_config import SmbConfig
from lumi.infrastructure.smb.connection import playback_uri, smb_uri_auth_user


def test_playback_uri_includes_credentials_and_path() -> None:
    config = SmbConfig.from_settings(
        Settings(
            mode="smb",
            smb_hostname="192.168.1.100",
            smb_share_name="media",
            smb_domain="EXAMPLE",
            smb_username="viewer",
            smb_password="secret",
        )
    )
    uri = playback_uri(config, PurePosixPath("Movies/Alien/Alien.mkv"))
    assert uri.startswith("smb://")
    assert "EXAMPLE/viewer:secret@" in uri
    assert "%5C" not in uri
    assert "192.168.1.100" in uri
    assert "media" in uri
    assert "Movies" in uri
    assert "Alien.mkv" in uri


def test_smb_uri_auth_user_uses_forward_slash_for_domain() -> None:
    config = SmbConfig.from_settings(
        Settings(
            mode="smb",
            smb_hostname="host",
            smb_share_name="share",
            smb_domain="WORKGROUP",
            smb_username="user",
        )
    )
    assert smb_uri_auth_user(config) == "WORKGROUP/user"
