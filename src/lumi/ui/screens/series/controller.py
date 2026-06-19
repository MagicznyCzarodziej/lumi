"""Series screen controller."""

from __future__ import annotations

from lumi.domain.library.library_repository import LibraryRepository
from lumi.ui.components.list_entry import ListEntryType, ListEntryUiModel
from lumi.ui.entry_handlers import push_episodes
from lumi.ui.layouts.list_with_poster_layout import ListWithPosterViewState
from lumi.ui.library_lookup import find_series
from lumi.ui.navigation.destinations import SeriesDestination
from lumi.ui.navigation.router import Router
from lumi.ui.strings import LIBRARY_LABEL


def build_series_state(
    destination: SeriesDestination,
    library_repository: LibraryRepository,
    router: Router,
) -> ListWithPosterViewState | None:
    series = find_series(library_repository.get_top_level_entries(), destination.series_id)
    if series is None:
        return None

    return ListWithPosterViewState(
        poster_path=series.root_relative_poster_path,
        breadcrumbs=LIBRARY_LABEL,
        title=series.name.name,
        subtitle=series.name.alternative_name,
        tags=series.tags,
        entries=[
            ListEntryUiModel(
                name=season.name,
                entry_type=ListEntryType.playables_group(len(season.episodes)),
                poster_path=season.root_relative_poster_path,
                on_click=push_episodes(router, season.id.id),
            )
            for season in series.seasons
        ],
    )
