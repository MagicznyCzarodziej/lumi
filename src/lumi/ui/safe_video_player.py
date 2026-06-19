"""Safe video playback wrapper for the UI layer."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import PurePosixPath

from lumi.domain.video_player import VideoPlaybackError, VideoPlayer


class SafeVideoPlayer:
    """Delegates to a VideoPlayer and routes launch failures to a callback."""

    def __init__(
        self,
        player: VideoPlayer,
        on_error: Callable[[str], None],
    ) -> None:
        self._player = player
        self._on_error = on_error

    def play_video(self, absolute_path: PurePosixPath) -> None:
        try:
            self._player.play_video(absolute_path)
        except VideoPlaybackError as exc:
            self._on_error(str(exc))
