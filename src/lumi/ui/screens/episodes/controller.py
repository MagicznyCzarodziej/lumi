"""Episodes screen controller."""

from __future__ import annotations

from lumi.domain.library.library_repository import LibraryRepository
from lumi.domain.video_player import VideoPlayer
from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel
from lumi.ui.entry_handlers import play_video
from lumi.ui.layouts.list_with_poster_layout import ListWithPosterViewState
from lumi.ui.library_lookup import find_episodes_group
from lumi.ui.navigation.destinations import EpisodesGroupDestination
from lumi.ui.strings import LIBRARY_LABEL


def build_episodes_state(
    destination: EpisodesGroupDestination,
    library_repository: LibraryRepository,
    video_player: VideoPlayer,
) -> ListWithPosterViewState | None:
    entries_list = library_repository.get_top_level_entries()
    series, episodes_group = find_episodes_group(entries_list, destination.episodes_group_id)
    if episodes_group is None:
        return None

    breadcrumbs = LIBRARY_LABEL
    tags = series.tags if series is not None else frozenset()
    if series is not None:
        breadcrumbs = f"{LIBRARY_LABEL} / {series.name.name}"

    return ListWithPosterViewState(
        poster_path=episodes_group.root_relative_poster_path,
        breadcrumbs=breadcrumbs,
        title=episodes_group.name.name,
        tags=tags,
        entries=[
            ListEntryUiModel(
                name=episode.name,
                entry_type=ListEntryType.single(),
                poster_path=episodes_group.root_relative_poster_path,
                on_click=play_video(video_player, episode.root_relative_path),
            )
            for episode in episodes_group.episodes
        ],
    )
