"""Tests for persisted video aspect ratio."""

from __future__ import annotations

import json
from pathlib import PurePosixPath

from lumi.domain.video_aspect import VideoAspectMode
from lumi.infrastructure.video_aspect_preferences import load_video_aspect, save_video_aspect


def test_load_video_aspect_returns_none_when_missing(tmp_path) -> None:
    path = tmp_path / "video_aspect.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")
    assert load_video_aspect(library_path, path=path) is None


def test_save_and_load_video_aspect(tmp_path) -> None:
    path = tmp_path / "video_aspect.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")
    save_video_aspect(library_path, VideoAspectMode.WIDE_16_9, path=path)
    assert load_video_aspect(library_path, path=path) == VideoAspectMode.WIDE_16_9
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "Movies/Alien/Alien.mkv": "16:9",
    }


def test_load_video_aspect_matches_leading_slash_key(tmp_path) -> None:
    path = tmp_path / "video_aspect.json"
    path.write_text(json.dumps({"/Filmy/16 Blocks/16 Blocks.mp4": "2.35:1"}), encoding="utf-8")
    loaded = load_video_aspect(PurePosixPath("Filmy/16 Blocks/16 Blocks.mp4"), path=path)
    assert loaded == VideoAspectMode.CINEMA_2_35
