"""Playback URI resolution for embedded video player."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol


class PlaybackUriResolver(Protocol):
    def playback_uri(self, absolute_path: PurePosixPath) -> str: ...
