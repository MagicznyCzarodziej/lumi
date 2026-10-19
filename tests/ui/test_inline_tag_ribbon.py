"""Inline tag ribbon widget tests."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from lumi.ui.components.inline_tag_ribbon import InlineTagRibbon


def _button_with_text(ribbon: InlineTagRibbon, text: str) -> QPushButton:
    return next(button for button in ribbon.findChildren(QPushButton) if button.text() == text)


def test_tag_selection_emits_filter_value_and_all_clears_it(qtbot) -> None:
    ribbon = InlineTagRibbon()
    qtbot.addWidget(ribbon)
    ribbon.set_tags(["action", "drama"])
    ribbon.show()
    qtbot.waitExposed(ribbon)

    selected: list[object] = []
    ribbon.tag_selected.connect(selected.append)

    qtbot.mouseClick(_button_with_text(ribbon, "Action"), Qt.MouseButton.LeftButton)
    qtbot.mouseClick(_button_with_text(ribbon, "All"), Qt.MouseButton.LeftButton)

    assert selected == ["action", None]


def test_boundary_arrow_keys_emit_focus_intents(qtbot) -> None:
    ribbon = InlineTagRibbon()
    qtbot.addWidget(ribbon)
    ribbon.set_tags(["action"])
    ribbon.show()
    qtbot.waitExposed(ribbon)

    previous_requested: list[bool] = []
    next_requested: list[bool] = []
    ribbon.focus_previous_requested.connect(lambda: previous_requested.append(True))
    ribbon.focus_next_requested.connect(lambda: next_requested.append(True))

    first = _button_with_text(ribbon, "All")
    first.setFocus()
    qtbot.keyClick(first, Qt.Key.Key_Left)

    last = _button_with_text(ribbon, "Action")
    last.setFocus()
    qtbot.keyClick(last, Qt.Key.Key_Right)

    assert previous_requested == [True]
    assert next_requested == [True]
