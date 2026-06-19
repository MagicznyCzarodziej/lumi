"""Default cache directory resolution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from lumi.config.settings import Settings


def default_cache_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "lumi" / "Cache"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "lumi"
    cache_home = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache_home) if cache_home else Path.home() / ".cache"
    return base / "lumi"


def default_config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "lumi"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "lumi"
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home) if config_home else Path.home() / ".config"
    return base / "lumi"


def library_cache_path(settings: Settings) -> Path:
    if settings.cache_library_json:
        return Path(settings.cache_library_json)
    return default_cache_dir() / "library_cache.json"


def poster_cache_dir(settings: Settings) -> Path:
    if settings.cache_posters:
        return Path(settings.cache_posters)
    return default_cache_dir() / "posters"


def player_preferences_path() -> Path:
    return default_config_dir() / "player.json"
