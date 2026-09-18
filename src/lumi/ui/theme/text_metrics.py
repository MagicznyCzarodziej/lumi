"""Font metrics helpers for custom-painted text."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics

from lumi.ui.theme.scale import scaled as s

# Extra ink padding so drawText does not clip descenders or side bearings on HiDPI/Linux.
TEXT_INK_PAD = max(2, s(2))

_WORD_WRAP_FLAGS = (
    int(Qt.AlignmentFlag.AlignLeft)
    | int(Qt.AlignmentFlag.AlignTop)
    | int(Qt.TextFlag.TextWordWrap)
)


def ink_single_line_height(metrics: QFontMetrics, text: str) -> int:
    sample = text or "Hg"
    ink = max(metrics.boundingRect(sample).height(), metrics.ascent() + metrics.descent())
    return ink + TEXT_INK_PAD


def ink_text_width(metrics: QFontMetrics, text: str) -> int:
    sample = text or " "
    return max(
        metrics.horizontalAdvance(sample),
        metrics.tightBoundingRect(sample).width(),
    ) + TEXT_INK_PAD


def ink_wrapped_text_height(text: str, font: QFont, width: int) -> int:
    if not text:
        return 0
    metrics = QFontMetrics(font)
    constraint = max(1, width)
    if metrics.horizontalAdvance(text) <= constraint:
        return ink_single_line_height(metrics, text)
    bounds = metrics.boundingRect(0, 0, constraint, 10_000, _WORD_WRAP_FLAGS, text)
    return bounds.height() + TEXT_INK_PAD
