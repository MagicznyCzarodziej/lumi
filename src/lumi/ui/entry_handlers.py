"""Typed click handlers for list entry view models."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import PurePosixPath

from lumi.domain.video_player import VideoPlayer
from lumi.ui.navigation.destinations import EpisodesGroupDestination, MediaGroupingEpisodesGroupDestination
from lumi.ui.navigation.router import Router


def play_video(player: VideoPlayer, path: PurePosixPath) -> Callable[[], None]:
    def handler() -> None:
        player.play_video(path)

    return handler


def push_episodes(router: Router, episodes_group_id: str) -> Callable[[], None]:
    def handler() -> None:
        router.push(EpisodesGroupDestination(episodes_group_id=episodes_group_id))

    return handler


def push_media_grouping_episodes(
    router: Router,
    media_grouping_id: str,
    episodes_group_id: str,
) -> Callable[[], None]:
    def handler() -> None:
        router.push(
            MediaGroupingEpisodesGroupDestination(
                media_grouping_id=media_grouping_id,
                episodes_group_id=episodes_group_id,
            )
        )

    return handler
