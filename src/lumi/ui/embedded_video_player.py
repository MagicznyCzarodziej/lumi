"""Embedded libmpv video player wired to the UI layer."""

from __future__ import annotations

import logging
from pathlib import PurePosixPath

from lumi.domain.playback import PlaybackUriResolver
from lumi.domain.video_player import VideoPlaybackError
from lumi.ui.player.host import PlayerHost

logger = logging.getLogger(__name__)


class EmbeddedVideoPlayer:
    """Opens the in-app mpv player for a library video path."""

    def __init__(self, playback_uri_resolver: PlaybackUriResolver, host: PlayerHost) -> None:
        self._playback_uri_resolver = playback_uri_resolver
        self._host = host

    def play_video(self, absolute_path: PurePosixPath) -> None:
        try:
            uri = self._playback_uri_resolver.playback_uri(absolute_path)
        except Exception as exc:
            raise VideoPlaybackError(f"Could not resolve playback URI: {exc}") from exc

        logger.info("Playing (embedded): %s", absolute_path)
        try:
            self._host.play(uri)
        except Exception as exc:
            raise VideoPlaybackError(f"Failed to start embedded player: {exc}") from exc
