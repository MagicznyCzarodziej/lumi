"""Mock video player — logs instead of launching external player."""

from __future__ import annotations

import logging
from pathlib import PurePosixPath

from lumi.domain.video_player import VideoPlayer

logger = logging.getLogger(__name__)


class MockVideoPlayer(VideoPlayer):
    def play_video(self, absolute_path: PurePosixPath) -> None:
        logger.info("Mock play: %s", absolute_path)
