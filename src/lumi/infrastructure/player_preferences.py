"""Persisted player UI preferences (volume, etc.)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from lumi.infrastructure.paths import player_preferences_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlayerPreferences:
    volume: int = 100


def _clamp_volume(value: float) -> int:
    return max(0, min(100, round(value)))


def load_player_preferences(*, path: Path | None = None) -> PlayerPreferences:
    prefs_path = path or player_preferences_path()

    if not prefs_path.is_file():
        return PlayerPreferences()

    try:
        with prefs_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read player preferences from %s: %s", prefs_path, exc)
        return PlayerPreferences()

    if not isinstance(data, dict):
        return PlayerPreferences()

    raw_volume = data.get("volume", 100)

    try:
        volume = _clamp_volume(float(raw_volume))
    except (TypeError, ValueError):
        volume = 100

    return PlayerPreferences(volume=volume)


def save_player_volume(volume: float, *, path: Path | None = None) -> None:
    prefs_path = path or player_preferences_path()
    clamped = _clamp_volume(volume)
    payload = {"volume": clamped}

    try:
        prefs_path.parent.mkdir(parents=True, exist_ok=True)
        with prefs_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
    except OSError as exc:
        logger.warning("Could not save player volume to %s: %s", prefs_path, exc)
