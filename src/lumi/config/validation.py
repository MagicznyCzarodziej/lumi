"""Application settings validation."""

from __future__ import annotations

from lumi.config.settings import Settings


class SettingsValidationError(ValueError):
    """Raised when required settings are missing for the selected mode."""


def validate_settings_for_mode(settings: Settings) -> None:
    if settings.mode != "smb":
        return

    missing = [
        name
        for name, value in (
            ("smb.hostname", settings.smb_hostname),
            ("smb.share_name", settings.smb_share_name),
            ("smb.username", settings.smb_username),
        )
        if not str(value).strip()
    ]
    if missing:
        raise SettingsValidationError(f"Missing required SMB settings: {', '.join(missing)}")
