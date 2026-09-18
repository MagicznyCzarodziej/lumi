"""List entry delegate sizing tests."""

from __future__ import annotations

from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication

from lumi.ui.components.list_entry_delegate.list_entry_delegate import _title_font, _wrapped_text_height
from lumi.ui.theme.text_metrics import ink_single_line_height


def test_single_line_height_uses_ink_bounds() -> None:
    QApplication.instance() or QApplication([])
    font = _title_font()
    metrics = QFontMetrics(font)
    height = ink_single_line_height(metrics, "gy")
    assert height >= metrics.ascent() + metrics.descent()
    assert height <= metrics.lineSpacing() + 4


def test_wrapped_text_height_stays_single_line_for_short_titles() -> None:
    QApplication.instance() or QApplication([])
    font = _title_font()
    metrics = QFontMetrics(font)
    height = _wrapped_text_height("Alien", font, 800)
    assert height == ink_single_line_height(metrics, "Alien")
