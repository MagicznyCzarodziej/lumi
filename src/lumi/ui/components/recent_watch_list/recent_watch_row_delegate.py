"""Selection chrome for recently watched list items."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from lumi.ui.theme.colors import LIST_SELECTION_ACCENT, LIST_SELECTION_TINT
from lumi.ui.theme.spacing import LIST_SELECTION_ACCENT_WIDTH, RECENT_WATCH_ROW_SPACING


class RecentWatchRowDelegate(QStyledItemDelegate):
    """Paints A3 row selection on the full list item rect (prototype ``.recent-row.selected``)."""

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index,  # noqa: ANN001 — Qt index type
    ) -> None:
        del index
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if not selected:
            return

        painter.save()
        row_rect = option.rect.adjusted(0, 0, 0, -RECENT_WATCH_ROW_SPACING)
        painter.fillRect(row_rect, QColor(LIST_SELECTION_TINT))
        painter.fillRect(
            row_rect.left(),
            row_rect.top(),
            LIST_SELECTION_ACCENT_WIDTH,
            row_rect.height(),
            QColor(LIST_SELECTION_ACCENT),
        )
        painter.restore()
