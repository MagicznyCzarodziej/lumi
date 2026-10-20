"""Top bar geometry vs A3 prototype chrome-top."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLineEdit, QWidget

from lumi.ui.components.inline_tag_ribbon.inline_tag_ribbon import _TagRibbonButton
from lumi.ui.components.top_bar import TopBar
from lumi.ui.theme.spacing import (
    DIVIDER_HEIGHT,
    TOPBAR_CHROME_GAP,
    TOPBAR_DIVIDER_MARGIN_H,
    TOPBAR_FILTER_GAP,
    TOPBAR_HIT_TARGET,
    TOPBAR_SEARCH_INNER_GAP,
    TOPBAR_SEARCH_PADDING_H,
    TOPBAR_SEARCH_PADDING_V,
)


def test_top_bar_chrome_matches_prototype_metrics(qtbot) -> None:
    top_bar = TopBar()
    qtbot.addWidget(top_bar)
    top_bar.resize(900, 120)
    top_bar.show()
    qtbot.waitExposed(top_bar)

    assert top_bar._recent_button.width() == TOPBAR_HIT_TARGET
    assert top_bar._recent_button.height() == TOPBAR_HIT_TARGET
    assert top_bar._search_pill.height() == TOPBAR_HIT_TARGET

    search = top_bar.findChild(QLineEdit, "searchField")
    assert search is not None
    pill_layout = top_bar._search_pill.layout()
    assert pill_layout is not None
    left, top, right, bottom = (
        pill_layout.contentsMargins().left(),
        pill_layout.contentsMargins().top(),
        pill_layout.contentsMargins().right(),
        pill_layout.contentsMargins().bottom(),
    )
    assert left == TOPBAR_SEARCH_PADDING_H
    assert right == TOPBAR_SEARCH_PADDING_H
    assert top == TOPBAR_SEARCH_PADDING_V
    assert bottom == TOPBAR_SEARCH_PADDING_V
    assert pill_layout.spacing() == TOPBAR_SEARCH_INNER_GAP

    filter_host = top_bar.findChild(QWidget, "filterIcons")
    assert filter_host is not None
    filter_layout = filter_host.layout()
    assert filter_layout is not None
    assert filter_layout.spacing() == TOPBAR_FILTER_GAP

    divider = top_bar.findChild(QFrame, "topBarDivider")
    assert divider is not None
    assert divider.height() == DIVIDER_HEIGHT

    divider_host = top_bar.findChild(QWidget, "topBarDividerHost")
    assert divider_host is not None
    divider_host_layout = divider_host.layout()
    assert divider_host_layout is not None
    assert divider_host_layout.contentsMargins().left() == TOPBAR_DIVIDER_MARGIN_H
    assert divider_host_layout.contentsMargins().right() == TOPBAR_DIVIDER_MARGIN_H

    controls = top_bar.layout().itemAt(0).layout()
    assert controls is not None
    assert controls.spacing() == TOPBAR_CHROME_GAP


def test_tag_chips_match_chrome_hit_target_height(qtbot) -> None:
    top_bar = TopBar()
    qtbot.addWidget(top_bar)
    top_bar.set_tags(["action"])
    top_bar.show()
    qtbot.waitExposed(top_bar)

    chips = top_bar.findChildren(_TagRibbonButton)
    assert chips
    for chip in chips:
        assert chip.height() == TOPBAR_HIT_TARGET
