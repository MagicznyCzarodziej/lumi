"""Media grouping screen controller."""

from __future__ import annotations

from lumi.domain.library.library_repository import LibraryRepository
from lumi.domain.library.models import EpisodesGroup, MediaGroupingFilm
from lumi.domain.video_player import VideoPlayer
from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel
from lumi.ui.entry_handlers import play_video, push_media_grouping_episodes
from lumi.ui.layouts.list_with_poster_layout import ListWithPosterViewState
from lumi.ui.library_lookup import find_media_grouping
from lumi.ui.navigation.destinations import MediaGroupingDestination
from lumi.ui.navigation.router import Router
from lumi.ui.strings import LIBRARY_LABEL


def build_media_grouping_state(
    destination: MediaGroupingDestination,
    library_repository: LibraryRepository,
    video_player: VideoPlayer,
    router: Router,
) -> ListWithPosterViewState | None:
    grouping = find_media_grouping(library_repository.get_top_level_entries(), destination.media_grouping_id)
    if grouping is None:
        return None

    entries: list[ListEntryUiModel] = []
    for child in grouping.entries:
        if isinstance(child, EpisodesGroup):
            entries.append(
                ListEntryUiModel(
                    name=child.name,
                    entry_type=ListEntryType.playables_group(len(child.episodes)),
                    poster_path=child.root_relative_poster_path,
                    on_click=push_media_grouping_episodes(router, grouping.id.id, child.id.id),
                )
            )
        elif isinstance(child, MediaGroupingFilm) and child.video_files:
            entries.append(
                ListEntryUiModel(
                    name=child.name,
                    entry_type=ListEntryType.single(),
                    poster_path=child.root_relative_poster_path,
                    on_click=play_video(video_player, child.video_files[0].absolute_path),
                )
            )

    return ListWithPosterViewState(
        poster_path=grouping.root_relative_poster_path,
        breadcrumbs=LIBRARY_LABEL,
        title=grouping.name.name,
        subtitle=grouping.name.alternative_name,
        tags=grouping.tags,
        entries=entries,
    )
