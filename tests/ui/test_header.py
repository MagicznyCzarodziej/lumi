"""Header layout tests."""

from __future__ import annotations

from lumi.ui.layouts.header.header import Header, _TagChip
from lumi.ui.theme.spacing import HEADER_TAG_GAP


def test_header_places_tags_in_a_compact_horizontal_ribbon(qtbot) -> None:
    header = Header()
    qtbot.addWidget(header)
    header.set_content(
        breadcrumbs="Library",
        title="Series",
        tags=frozenset({"action", "drama"}),
    )
    header.resize(800, 200)
    header.show()
    qtbot.waitExposed(header)

    chips = header.findChildren(_TagChip)

    assert len(chips) == 2
    assert chips[0].y() == chips[1].y()
    assert chips[1].x() - chips[0].x() - chips[0].width() == HEADER_TAG_GAP
