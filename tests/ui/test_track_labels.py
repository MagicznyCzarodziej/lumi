"""Track label tests."""

from __future__ import annotations

from lumi.ui.player.controller.track_labels import external_subtitle_basename, subtitle_track_label


def test_subtitle_track_label_uses_external_filename() -> None:
    track = {
        "id": 3,
        "type": "sub",
        "title": "txt",
        "external-filename": "http://127.0.0.1:1234/stream/abc/Sherlock.en.txt",
    }
    assert subtitle_track_label(track) == "Sherlock.en.txt"


def test_subtitle_track_label_prefers_display_name() -> None:
    track = {"id": 3, "type": "sub", "title": "txt"}
    assert subtitle_track_label(track, display_name="Sherlock.en.txt") == "Sherlock.en.txt"


def test_external_subtitle_basename_strips_stream_url() -> None:
    track = {
        "external-filename": "http://127.0.0.1/stream/token/Movie.srt",
    }
    assert external_subtitle_basename(track) == "Movie.srt"
