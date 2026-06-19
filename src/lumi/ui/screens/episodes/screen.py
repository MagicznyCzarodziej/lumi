"""Episodes list screen."""

from __future__ import annotations

from lumi.ui.context import ScreenContext
from lumi.ui.layouts.list_with_poster_layout import ListWithPosterLayout, ListWithPosterViewState
from lumi.ui.navigation.destinations import Destination, EpisodesGroupDestination
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.screens.episodes.controller import build_episodes_state
from lumi.ui.screens.list_with_poster_screen import ListWithPosterScreen
from lumi.ui.strings import LIBRARY_LABEL


class EpisodesScreen(ListWithPosterScreen):
    def __init__(self, *, poster_loader: PosterLoader | None = None) -> None:
        layout = ListWithPosterLayout()
        if poster_loader is not None:
            layout.set_poster_loader(poster_loader)
        super().__init__(layout)

    def bind(self, destination: Destination, context: ScreenContext) -> None:
        if not isinstance(destination, EpisodesGroupDestination):
            return
        state = build_episodes_state(destination, context.library_repository, context.video_player)
        self.apply_state(
            state or ListWithPosterViewState(breadcrumbs=LIBRARY_LABEL, title="Episodes not found")
        )
