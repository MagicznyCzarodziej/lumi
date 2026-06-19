"""Series detail screen."""

from __future__ import annotations

from lumi.ui.context import ScreenContext
from lumi.ui.layouts.list_with_poster_layout import ListWithPosterLayout, ListWithPosterViewState
from lumi.ui.navigation.destinations import Destination, SeriesDestination
from lumi.ui.navigation.router import Router
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.screens.list_with_poster_screen import ListWithPosterScreen
from lumi.ui.screens.series.controller import build_series_state
from lumi.ui.strings import LIBRARY_LABEL


class SeriesScreen(ListWithPosterScreen):
    def __init__(self, router: Router, *, poster_loader: PosterLoader | None = None) -> None:
        layout = ListWithPosterLayout()
        if poster_loader is not None:
            layout.set_poster_loader(poster_loader)
        super().__init__(layout)
        self._router = router

    def bind(self, destination: Destination, context: ScreenContext) -> None:
        if not isinstance(destination, SeriesDestination):
            return
        state = build_series_state(destination, context.library_repository, self._router)
        self.apply_state(state or _missing_state(destination.series_id))


def _missing_state(entry_id: str) -> ListWithPosterViewState:
    return ListWithPosterViewState(breadcrumbs=LIBRARY_LABEL, title=f"Not found: {entry_id}")
