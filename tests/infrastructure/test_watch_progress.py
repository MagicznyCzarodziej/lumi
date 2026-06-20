"""Tests for persisted watch progress."""

from __future__ import annotations

import json
from pathlib import PurePosixPath

from lumi.infrastructure.watch_progress import (
    load_watch_position,
    save_watch_position,
)


def test_load_watch_position_returns_none_when_missing(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")
    assert load_watch_position(library_path, path=path) is None


def test_save_and_load_watch_position(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")

    save_watch_position(library_path, 1234.567, duration=7200.0, path=path)

    assert load_watch_position(library_path, duration=7200.0, path=path) == 1234.567
    assert json.loads(path.read_text(encoding="utf-8")) == {"/Movies/Alien/Alien.mkv": 1234.567}


def test_save_watch_position_does_not_persist_near_start(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")

    save_watch_position(library_path, 2.0, duration=7200.0, path=path)

    assert not path.exists() or load_watch_position(library_path, duration=7200.0, path=path) is None


def test_save_watch_position_clears_near_end(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")

    save_watch_position(library_path, 1000.0, duration=7200.0, path=path)
    save_watch_position(library_path, 7180.0, duration=7200.0, path=path)

    assert load_watch_position(library_path, duration=7200.0, path=path) is None
    assert json.loads(path.read_text(encoding="utf-8")) == {}


def test_load_watch_position_rejects_near_end_for_known_duration(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")
    path.write_text(json.dumps({"/Movies/Alien/Alien.mkv": 7000.0}), encoding="utf-8")

    assert load_watch_position(library_path, duration=7200.0, path=path) is None


def test_save_watch_position_updates_existing_entry(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    first = PurePosixPath("/Movies/Alien/Alien.mkv")
    second = PurePosixPath("/Movies/Blade Runner/Blade Runner.mkv")

    save_watch_position(first, 100.0, duration=7200.0, path=path)
    save_watch_position(second, 200.0, duration=7200.0, path=path)
    save_watch_position(first, 150.0, duration=7200.0, path=path)

    assert load_watch_position(first, duration=7200.0, path=path) == 150.0
    assert load_watch_position(second, duration=7200.0, path=path) == 200.0
