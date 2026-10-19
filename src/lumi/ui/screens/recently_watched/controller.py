"""View state construction for the Recently Watched screen."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import PurePosixPath

from lumi.domain.library.models import (
    Library,
    LibraryEntry,
    MediaGrouping,
    Series,
)
from lumi.domain.recent_watch import RecentWatchRecord, ResolvedRecentWatch, resolve_recent_watch_records
from lumi.domain.video_player import VideoPlayer
from lumi.ui.navigation.destinations import (
    EpisodesGroupDestination,
    MediaGroupingEpisodesGroupDestination,
)
from lumi.ui.navigation.router import Router


class RecentWatchAction(Enum):
    """Actions offered for a recently watched item."""

    RESUME = auto()
    EPISODES = auto()


@dataclass(frozen=True)
class RecentWatchRowUiModel:
    """One visible recent-watch row and its keyboard actions."""

    playback_path: PurePosixPath
    poster_path: PurePosixPath | None
    playable_name: str
    show_name: str | None
    alternative_name: str | None
    time_label: str
    progress_fraction: float
    actions: tuple[RecentWatchAction, ...]
    _action_handlers: dict[RecentWatchAction, Callable[[], None]]

    def activate(self, action: RecentWatchAction) -> None:
        """Run a visible row action."""
        self._action_handlers[action]()


@dataclass(frozen=True)
class RecentlyWatchedUiState:
    rows: list[RecentWatchRowUiModel]


def build_recently_watched_state(
    records: Iterable[RecentWatchRecord],
    entries: list[LibraryEntry],
    router: Router,
    video_player: VideoPlayer,
) -> RecentlyWatchedUiState:
    """Resolve persisted watches into ordered, actionable screen rows."""
    resolved = resolve_recent_watch_records(records, Library(entries))
    return RecentlyWatchedUiState(
        rows=[
            _row_for_recent_watch(item, router=router, video_player=video_player)
            for item in resolved
        ]
    )


def _row_for_recent_watch(
    item: ResolvedRecentWatch,
    *,
    router: Router,
    video_player: VideoPlayer,
) -> RecentWatchRowUiModel:
    actions = [RecentWatchAction.RESUME]
    handlers: dict[RecentWatchAction, Callable[[], None]] = {
        RecentWatchAction.RESUME: lambda: video_player.play_video(item.library_path),
    }
    if destination := _episodes_destination(item):
        actions.append(RecentWatchAction.EPISODES)
        handlers[RecentWatchAction.EPISODES] = lambda: router.push(destination)

    duration = item.duration
    progress = 0.0 if duration is None else min(1.0, max(0.0, item.position / duration))
    return RecentWatchRowUiModel(
        playback_path=item.library_path,
        poster_path=item.entry.root_relative_poster_path,
        playable_name=item.playable_name.name,
        show_name=item.entry.name.name if item.episode is not None else None,
        alternative_name=(
            item.playable_name.alternative_name or item.entry.name.alternative_name
        ),
        time_label=_time_label(item.position, duration),
        progress_fraction=progress,
        actions=tuple(actions),
        _action_handlers=handlers,
    )


def _episodes_destination(
    item: ResolvedRecentWatch,
) -> EpisodesGroupDestination | MediaGroupingEpisodesGroupDestination | None:
    group = item.episodes_group
    if group is None:
        return None

    entry = item.entry
    if isinstance(entry, Series):
        return EpisodesGroupDestination(episodes_group_id=group.id.id)
    if isinstance(entry, MediaGrouping):
        return MediaGroupingEpisodesGroupDestination(
            media_grouping_id=entry.id.id,
            episodes_group_id=group.id.id,
        )
    return None


def _time_label(position: float, duration: float | None) -> str:
    if duration is None:
        return _format_time(position)
    return f"{_format_time(position)} / {_format_time(duration)}"


def _format_time(seconds: float) -> str:
    whole_seconds = max(0, int(seconds))
    minutes, seconds = divmod(whole_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
