"""Narrow dependencies passed from the composition root into screens."""

from __future__ import annotations

from dataclasses import dataclass

from lumi.domain.library.library_repository import LibraryRepository
from lumi.domain.video_player import VideoPlayer


@dataclass(frozen=True)
class ScreenContext:
    library_repository: LibraryRepository
    video_player: VideoPlayer
