"""Settings validation tests."""

from __future__ import annotations

import pytest

from lumi.config.settings import Settings, get_settings
from lumi.config.validation import SettingsValidationError, validate_settings_for_mode


def test_validate_settings_for_mode_allows_mock() -> None:
    validate_settings_for_mode(Settings(mode="mock"))


def test_validate_settings_for_mode_requires_smb_fields() -> None:
    with pytest.raises(SettingsValidationError, match="smb.hostname"):
        validate_settings_for_mode(Settings(mode="smb"))


def test_validate_settings_for_mode_accepts_complete_smb_config() -> None:
    validate_settings_for_mode(
        Settings(
            mode="smb",
            smb={"hostname": "192.168.1.100", "share_name": "share", "username": "user"},
        )
    )


def test_smb_hostname_coerced_from_yaml_float() -> None:
    settings = Settings(smb_hostname=10.0)
    assert settings.smb_hostname == "10.0"


def test_library_root_env_override(tmp_path, monkeypatch) -> None:
    missing = tmp_path / "missing.yaml"
    monkeypatch.setenv("LUMI_CONFIG", str(missing))
    monkeypatch.setenv("LUMI_LIBRARY_ROOT", "/Custom")
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.library_root == "/Custom"

    get_settings.cache_clear()


def test_default_mode_is_mock() -> None:
    settings = Settings()
    assert settings.mode == "mock"


def test_get_settings_without_config_file(tmp_path, monkeypatch) -> None:
    missing = tmp_path / "missing.yaml"
    monkeypatch.setenv("LUMI_CONFIG", str(missing))
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.mode == "mock"
    assert settings.library_root == ""

    get_settings.cache_clear()
