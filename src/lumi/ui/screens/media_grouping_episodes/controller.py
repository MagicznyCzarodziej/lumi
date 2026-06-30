"""Media grouping episodes controller."""

from __future__ import annotations

from lumi.domain.library.library_repository import LibraryRepository
from lumi.domain.video_player import VideoPlayer
from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel
from lumi.ui.entry_handlers import play_video
from lumi.ui.layouts.list_with_poster_layout import ListWithPosterViewState
from lumi.ui.library_lookup import find_media_grouping_episodes_group
from lumi.ui.navigation.destinations import MediaGroupingEpisodesGroupDestination
from lumi.ui.strings import LIBRARY_LABEL


def build_media_grouping_episodes_state(
    destination: MediaGroupingEpisodesGroupDestination,
    library_repository: LibraryRepository,
    video_player: VideoPlayer,
) -> ListWithPosterViewState | None:
    entries_list = library_repository.get_top_level_entries()
    grouping, episodes_group = find_media_grouping_episodes_group(
        entries_list,
        destination.media_grouping_id,
        destination.episodes_group_id,
    )
    if grouping is None or episodes_group is None:
        return None

    return ListWithPosterViewState(
        poster_path=episodes_group.root_relative_poster_path,
        breadcrumbs=f"{LIBRARY_LABEL} / {grouping.name.name}",
        title=episodes_group.name.name,
        tags=grouping.tags,
        entries=[
            ListEntryUiModel(
                name=episode.name,
                entry_type=ListEntryType.single(),
                poster_path=episodes_group.root_relative_poster_path,
                playback_path=episode.root_relative_path,
                on_click=play_video(video_player, episode.root_relative_path),
            )
            for episode in episodes_group.episodes
        ],
    )
