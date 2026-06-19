"""SMB connection helper tests."""

from lumi.config.settings import Settings
from lumi.config.smb_config import SmbConfig
from lumi.infrastructure.smb.connection import format_smb_username


def test_format_smb_username_adds_domain() -> None:
    config = SmbConfig.from_settings(Settings(smb_domain="BANANAS", smb_username="lumi"))
    assert format_smb_username(config) == "BANANAS\\lumi"


def test_format_smb_username_preserves_existing_domain_prefix() -> None:
    config = SmbConfig.from_settings(Settings(smb_domain="WORKGROUP", smb_username="BANANAS\\lumi"))
    assert format_smb_username(config) == "BANANAS\\lumi"
