"""View state construction for the Recently Watched screen."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
from pathlib import PurePosixPath

from lumi.domain.library.models import (
    FilmSeries,
    Library,
    LibraryEntry,
    MediaGrouping,
    MediaGroupingFilm,
    Series,
)
from lumi.domain.recent_watch import (
    RecentWatchRecord,
    ResolvedRecentWatch,
    is_playback_complete,
    resolve_recent_watch_records,
    resume_timeline_fraction,
    video_files_refer_to_path,
)
from lumi.domain.video_player import VideoPlayer
from lumi.domain.watch_history import WatchHistory
from lumi.ui.navigation.destinations import (
    EpisodesGroupDestination,
    MediaGroupingEpisodesGroupDestination,
)
from lumi.ui.navigation.router import Router

class RecentWatchAction(Enum):
    """Actions offered for a recently watched item."""

    RESUME = auto()
    EPISODES = auto()
    REMOVE = auto()


@dataclass(frozen=True)
class RecentWatchRowUiModel:
    """One visible recent-watch row and its keyboard actions."""

    playback_path: PurePosixPath
    poster_path: PurePosixPath | None
    playable_name: str
    show_name: str | None
    alternative_name: str | None
    played_at_label: str
    resume_position_seconds: float
    media_duration_seconds: float | None
    progress_fraction: float
    resume_action_label: str
    actions: tuple[RecentWatchAction, ...]
    _action_handlers: dict[RecentWatchAction, Callable[[], None]]

    def activate(self, action: RecentWatchAction) -> None:
        """Run a visible row action."""
        self._action_handlers[action]()


@dataclass(frozen=True)
class RecentlyWatchedUiState:
    rows: list[RecentWatchRowUiModel]


_MAX_RECENT_ROWS = 30


def build_recently_watched_state(
    records: Iterable[RecentWatchRecord],
    entries: list[LibraryEntry],
    router: Router,
    video_player: VideoPlayer,
    *,
    watch_history: WatchHistory | None = None,
    on_entry_removed: Callable[[], None] | None = None,
) -> RecentlyWatchedUiState:
    """Resolve persisted watches into ordered, actionable screen rows."""
    resolved = resolve_recent_watch_records(records, Library(entries))[:_MAX_RECENT_ROWS]
    return RecentlyWatchedUiState(
        rows=[
            _row_for_recent_watch(
                item,
                router=router,
                video_player=video_player,
                watch_history=watch_history,
                on_entry_removed=on_entry_removed,
            )
            for item in resolved
        ]
    )


def _row_for_recent_watch(
    item: ResolvedRecentWatch,
    *,
    router: Router,
    video_player: VideoPlayer,
    watch_history: WatchHistory | None = None,
    on_entry_removed: Callable[[], None] | None = None,
) -> RecentWatchRowUiModel:
    actions = [RecentWatchAction.RESUME]
    handlers: dict[RecentWatchAction, Callable[[], None]] = {
        RecentWatchAction.RESUME: lambda: video_player.play_video(item.library_path),
    }
    if destination := _episodes_destination(item):
        actions.append(RecentWatchAction.EPISODES)
        handlers[RecentWatchAction.EPISODES] = lambda: router.push(destination)
    if watch_history is not None and on_entry_removed is not None:
        library_path = item.library_path

        def _remove_from_recent() -> None:
            watch_history.forget_playback(library_path)
            on_entry_removed()

        actions.append(RecentWatchAction.REMOVE)
        handlers[RecentWatchAction.REMOVE] = _remove_from_recent

    duration = item.duration
    progress = resume_timeline_fraction(item.position, duration) or 0.0
    resume_label = (
        "Watch again" if is_playback_complete(item.position, duration) else "Resume"
    )
    return RecentWatchRowUiModel(
        playback_path=item.library_path,
        poster_path=_poster_path_for(item),
        playable_name=item.playable_name.name,
        show_name=item.entry.name.name if item.episode is not None else None,
        alternative_name=(
            (item.playable_name.alternative_name or item.entry.name.alternative_name)
            if item.episode is not None
            else None
        ),
        played_at_label=_played_at_label(item.watched_at),
        resume_position_seconds=item.position,
        media_duration_seconds=duration,
        progress_fraction=progress,
        resume_action_label=resume_label,
        actions=tuple(actions),
        _action_handlers=handlers,
    )


def _poster_path_for(item: ResolvedRecentWatch) -> PurePosixPath | None:
    if item.episodes_group is not None:
        return item.episodes_group.root_relative_poster_path
    entry = item.entry
    if isinstance(entry, FilmSeries):
        for film in entry.films:
            if video_files_refer_to_path(film.video_files, item.library_path):
                return film.root_relative_poster_path
    if isinstance(entry, MediaGrouping):
        for child in entry.entries:
            if isinstance(child, MediaGroupingFilm) and video_files_refer_to_path(
                child.video_files, item.library_path
            ):
                return child.root_relative_poster_path
    return entry.root_relative_poster_path


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


def _played_at_label(watched_at: datetime) -> str:
    now = datetime.now(UTC)
    watched = watched_at.astimezone(UTC)
    day_diff = (now.date() - watched.date()).days
    if day_diff == 0:
        return "Today"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return f"{day_diff}d ago"
    return watched.strftime("%b %d")


