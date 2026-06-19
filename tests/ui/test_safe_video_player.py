"""SafeVideoPlayer tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import PurePosixPath
from unittest.mock import MagicMock

import pytest

from lumi.domain.video_player import VideoPlaybackError
from lumi.ui.safe_video_player import SafeVideoPlayer


def test_safe_video_player_reports_playback_errors() -> None:
    player = MagicMock()
    player.play_video.side_effect = VideoPlaybackError("External player not found: mpv")
    errors: list[str] = []

    SafeVideoPlayer(player, errors.append).play_video(MOCK_LIBRARY_ROOT / "Alien/Alien.mkv")

    assert errors == ["External player not found: mpv"]
    player.play_video.assert_called_once_with(MOCK_LIBRARY_ROOT / "Alien/Alien.mkv")


def test_safe_video_player_delegates_successful_playback() -> None:
    player = MagicMock()
    errors: list[str] = []

    SafeVideoPlayer(player, errors.append).play_video(MOCK_LIBRARY_ROOT / "Alien/Alien.mkv")

    assert errors == []
    player.play_video.assert_called_once()
