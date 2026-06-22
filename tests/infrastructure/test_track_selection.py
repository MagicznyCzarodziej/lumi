"""Tests for persisted track selection."""

from __future__ import annotations

import json
from pathlib import PurePosixPath

from lumi.infrastructure.track_selection import (
    SavedTrackSelection,
    load_track_selection,
    save_track_selection,
)


def test_load_track_selection_returns_none_when_missing(tmp_path) -> None:
    path = tmp_path / "track_selection.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")
    assert load_track_selection(library_path, path=path) is None


def test_save_and_load_track_selection(tmp_path) -> None:
    path = tmp_path / "track_selection.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")
    saved = SavedTrackSelection(
        aid=1,
        sid=3,
        subtitle_off=False,
        subtitle_label="Alien.srt",
        subtitle_path=PurePosixPath("/Movies/Alien/Alien.srt"),
    )
    save_track_selection(library_path, saved, path=path)

    loaded = load_track_selection(library_path, path=path)
    assert loaded == saved
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "Movies/Alien/Alien.mkv": {
            "aid": 1,
            "sid": 3,
            "subtitle_off": False,
            "subtitle_label": "Alien.srt",
            "subtitle_path": "/Movies/Alien/Alien.srt",
        }
    }


def test_load_track_selection_matches_leading_slash_key(tmp_path) -> None:
    path = tmp_path / "track_selection.json"
    path.write_text(
        json.dumps(
            {
                "/Filmy/12 Angry Men/12 Angry Men.mp4": {
                    "aid": 1,
                    "sid": 1,
                    "subtitle_off": False,
                    "subtitle_label": "12 Angry Men.srt",
                    "subtitle_path": None,
                }
            }
        ),
        encoding="utf-8",
    )
    loaded = load_track_selection(PurePosixPath("Filmy/12 Angry Men/12 Angry Men.mp4"), path=path)
    assert loaded == SavedTrackSelection(
        aid=1,
        sid=1,
        subtitle_off=False,
        subtitle_label="12 Angry Men.srt",
        subtitle_path=None,
    )


def test_save_track_selection_stores_subtitle_off(tmp_path) -> None:
    path = tmp_path / "track_selection.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")
    save_track_selection(
        library_path,
        SavedTrackSelection(aid=2, subtitle_off=True),
        path=path,
    )
    loaded = load_track_selection(library_path, path=path)
    assert loaded == SavedTrackSelection(aid=2, subtitle_off=True)
