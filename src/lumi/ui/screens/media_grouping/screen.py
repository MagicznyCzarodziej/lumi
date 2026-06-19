"""Media grouping detail screen."""

from __future__ import annotations

from lumi.ui.context import ScreenContext
from lumi.ui.layouts.list_with_poster_layout import ListWithPosterLayout, ListWithPosterViewState
from lumi.ui.navigation.destinations import Destination, MediaGroupingDestination
from lumi.ui.navigation.router import Router
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.screens.list_with_poster_screen import ListWithPosterScreen
from lumi.ui.screens.media_grouping.controller import build_media_grouping_state
from lumi.ui.strings import LIBRARY_LABEL


class MediaGroupingScreen(ListWithPosterScreen):
    def __init__(self, router: Router, *, poster_loader: PosterLoader | None = None) -> None:
        layout = ListWithPosterLayout()
        if poster_loader is not None:
            layout.set_poster_loader(poster_loader)
        super().__init__(layout)
        self._router = router

    def bind(self, destination: Destination, context: ScreenContext) -> None:
        if not isinstance(destination, MediaGroupingDestination):
            return
        state = build_media_grouping_state(
            destination,
            context.library_repository,
            context.video_player,
            self._router,
        )
        self.apply_state(state or ListWithPosterViewState(breadcrumbs=LIBRARY_LABEL, title="Grouping not found"))
