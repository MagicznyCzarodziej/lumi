"""Playback URI resolution for embedded video player."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol


class PlaybackUriResolver(Protocol):
    def playback_uri(self, absolute_path: PurePosixPath) -> str: ...

    def stream_uri(self, absolute_path: PurePosixPath) -> str: ...

    def resolve_path(self, hint_path: PurePosixPath) -> PurePosixPath: ...

    def resolve_share_file(self, hint_path: PurePosixPath) -> PurePosixPath: ...
