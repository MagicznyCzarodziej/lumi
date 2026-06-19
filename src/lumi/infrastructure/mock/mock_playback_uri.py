"""Mock playback URI resolver — returns POSIX path for local testing."""

from __future__ import annotations

from pathlib import PurePosixPath


class MockPlaybackUriResolver:
    def playback_uri(self, absolute_path: PurePosixPath) -> str:
        return absolute_path.as_posix()
