"""Tests for persisted player preferences."""

from __future__ import annotations

import json

from lumi.infrastructure.player_preferences import (
    PlayerPreferences,
    load_player_preferences,
    save_player_volume,
)


def test_load_player_preferences_returns_default_when_missing(tmp_path) -> None:
    path = tmp_path / "player.json"
    prefs = load_player_preferences(path=path)
    assert prefs == PlayerPreferences(volume=100)


def test_save_and_load_player_volume(tmp_path) -> None:
    path = tmp_path / "player.json"
    save_player_volume(37, path=path)
    prefs = load_player_preferences(path=path)
    assert prefs.volume == 37
    assert json.loads(path.read_text(encoding="utf-8")) == {"volume": 37}


def test_save_player_volume_rounds_to_int(tmp_path) -> None:
    path = tmp_path / "player.json"
    save_player_volume(37.6, path=path)
    assert load_player_preferences(path=path).volume == 38


def test_load_player_preferences_clamps_invalid_values(tmp_path) -> None:
    path = tmp_path / "player.json"
    path.write_text(json.dumps({"volume": 150}), encoding="utf-8")
    assert load_player_preferences(path=path).volume == 100

    path.write_text(json.dumps({"volume": -10}), encoding="utf-8")
    assert load_player_preferences(path=path).volume == 0

    path.write_text("not json", encoding="utf-8")
    assert load_player_preferences(path=path) == PlayerPreferences(volume=100)


def test_save_player_volume_clamps_before_write(tmp_path) -> None:
    path = tmp_path / "player.json"
    save_player_volume(120.0, path=path)
    assert load_player_preferences(path=path).volume == 100
