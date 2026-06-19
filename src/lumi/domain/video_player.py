"""External video playback interface."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol


class VideoPlaybackError(RuntimeError):
    """Raised when the external player cannot be launched."""


class VideoPlayer(Protocol):
    def play_video(self, absolute_path: PurePosixPath) -> None: ...
