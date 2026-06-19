"""Container wiring tests."""

from __future__ import annotations

import pytest

from lumi.config.settings import Settings
from lumi.config.validation import SettingsValidationError
from lumi.container import build_container


def test_build_container_rejects_incomplete_smb_settings() -> None:
    with pytest.raises(SettingsValidationError, match="smb.hostname"):
        build_container(Settings(mode="smb"))


def test_build_container_allows_mock_mode() -> None:
    container = build_container(Settings(mode="mock"))
    assert container.library_repository is not None
    container.shutdown()
