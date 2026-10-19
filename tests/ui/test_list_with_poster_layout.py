"""List-with-poster layout tests."""

from __future__ import annotations

from lumi.ui.layouts.list_with_poster_layout import ListWithPosterLayout
from lumi.ui.theme.spacing import LIST_LAYOUT_STRETCH, POSTER_LAYOUT_STRETCH


def test_layout_preserves_the_shared_poster_list_split(qtbot) -> None:
    layout = ListWithPosterLayout()
    qtbot.addWidget(layout)
    layout.resize(1_000, 600)
    layout.show()
    qtbot.waitExposed(layout)

    assert layout.poster_widget.width() == 1_000 * POSTER_LAYOUT_STRETCH // (
        POSTER_LAYOUT_STRETCH + LIST_LAYOUT_STRETCH
    )
