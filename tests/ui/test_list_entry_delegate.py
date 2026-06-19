"""List entry delegate sizing tests."""

from __future__ import annotations

from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication

from lumi.ui.components.list_entry_delegate.list_entry_delegate import (
    _line_paint_height,
    _title_font,
    _wrapped_text_height,
)


def test_line_paint_height_covers_descenders() -> None:
    QApplication.instance() or QApplication([])
    metrics = QFontMetrics(_title_font())
    sample = _wrapped_text_height("gy", _title_font(), 800)
    assert sample >= metrics.ascent() + metrics.descent()
    assert sample >= _line_paint_height(metrics)


def test_wrapped_text_height_matches_single_line_titles() -> None:
    QApplication.instance() or QApplication([])
    font = _title_font()
    height = _wrapped_text_height("Back to the Future", font, 800)
    assert height >= _line_paint_height(QFontMetrics(font))
