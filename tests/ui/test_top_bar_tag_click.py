"""Tag filter clicks through TopBar (library chrome stack)."""

from __future__ import annotations

from PySide6.QtCore import Qt

from lumi.ui.components.inline_tag_ribbon.inline_tag_ribbon import _TagRibbonButton
from lumi.ui.components.top_bar import TopBar


def test_top_bar_tag_click_emits_filter(qtbot) -> None:
    top_bar = TopBar()
    qtbot.addWidget(top_bar)
    top_bar.set_tags(["action", "drama"])
    top_bar.resize(900, 120)
    top_bar.show()
    qtbot.waitExposed(top_bar)

    selected: list[object] = []
    top_bar.tag_filter_changed.connect(selected.append)

    action = next(
        button for button in top_bar.findChildren(_TagRibbonButton) if button.text() == "Action"
    )
    qtbot.mouseClick(action, Qt.MouseButton.LeftButton)

    assert selected == ["action"]
