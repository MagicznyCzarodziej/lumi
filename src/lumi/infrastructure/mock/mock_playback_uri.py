"""Mock playback URI resolver — returns POSIX path for local testing."""

from __future__ import annotations

from pathlib import PurePosixPath


class MockPlaybackUriResolver:
    def playback_uri(self, absolute_path: PurePosixPath) -> str:
        return self.stream_uri(absolute_path)

    def resolve_path(self, hint_path: PurePosixPath) -> PurePosixPath:
        return hint_path

    def resolve_share_file(self, hint_path: PurePosixPath) -> PurePosixPath:
        return hint_path

    def stream_uri(self, absolute_path: PurePosixPath) -> str:
        return absolute_path.as_posix()
