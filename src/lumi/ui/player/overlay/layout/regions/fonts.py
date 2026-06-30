"""Font helpers for measuring label widths during layout."""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics


def ui_font(size: int, bold: bool = False) -> QFont:
    """System UI font at ``size`` pt — matches what paint delegates render."""
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    font.setPointSize(max(9, size))
    font.setBold(bold)
    return font


def time_label_width(fm: QFontMetrics, gap: int) -> int:
    """Reserve width for elapsed/total labels (widest plausible timestamp + gap)."""
    sample_w = max(
        fm.horizontalAdvance("0:00"),
        fm.horizontalAdvance("0:00:00"),
        fm.horizontalAdvance("99:59:59"),
    )
    return sample_w + gap
