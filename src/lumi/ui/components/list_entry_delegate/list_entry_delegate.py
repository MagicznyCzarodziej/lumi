"""Gradient list row delegate."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QSize
from PySide6.QtGui import QBrush, QFont, QFontMetrics, QLinearGradient, QPainter, QColor, QPainterPath
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem, QWidget

from lumi.ui.components.list_entry import ListEntryTypeKind, ListEntryUiModel, NameDisplayStrategy
from lumi.ui.icons.material_icons import IconKind, paint_icon
from lumi.ui.theme.colors import ENTRY_FOCUS_START, TEXT_MUTED, TEXT_PRIMARY
from lumi.ui.theme.spacing import (
    CORNER_RADIUS_SM,
    ICON_GAP_MD,
    ICON_GAP_SM,
    ICON_SIZE,
    LIST_ROW_MARGINS,
    LIST_ROW_SPACING,
)
from lumi.ui.theme.typography import FONT_SIZE_COUNT, FONT_SIZE_LIST, FONT_SIZE_LIST_ALT

_TEXT_FLAGS = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap


def _title_font() -> QFont:
    font = QFont()
    font.setPixelSize(FONT_SIZE_LIST)
    return font


def _alt_font() -> QFont:
    font = QFont()
    font.setPixelSize(FONT_SIZE_LIST_ALT)
    return font


def _line_paint_height(metrics: QFontMetrics) -> int:
    """One line of text — ascent+descent plus a little room for descenders/AA."""
    return metrics.ascent() + metrics.descent() + max(2, metrics.leading() // 2 + 1)


def _wrapped_text_height(text: str, font: QFont, width: int) -> int:
    if not text:
        return 0
    metrics = QFontMetrics(font)
    line_height = _line_paint_height(metrics)
    if width <= 0:
        return line_height
    bounds = metrics.boundingRect(0, 0, width, 10_000, int(_TEXT_FLAGS), text)
    if metrics.horizontalAdvance(text) <= width:
        return line_height
    return max(line_height, bounds.height() + max(2, metrics.descent() // 3))


def _draw_wrapped_text(
    painter: QPainter,
    *,
    text: str,
    font: QFont,
    rect: QRect,
) -> None:
    painter.setFont(font)
    painter.drawText(rect, _TEXT_FLAGS, text)


class ListEntryDelegate(QStyledItemDelegate):
    _CORNER_RADIUS = CORNER_RADIUS_SM
    _DEFAULT_CONTENT_MARGINS = LIST_ROW_MARGINS

    def __init__(
        self,
        *,
        name_display_strategy: NameDisplayStrategy = NameDisplayStrategy.REGULAR,
        content_margins: tuple[int, int, int, int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name_display_strategy = name_display_strategy
        left, top, right, bottom = content_margins or self._DEFAULT_CONTENT_MARGINS
        self._content_margins = (left, top, right, bottom)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        model = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(model, ListEntryUiModel):
            super().paint(painter, option, index)
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(option.rect)

        outer = option.rect
        row_rect = outer.adjusted(0, 0, 0, -LIST_ROW_SPACING)
        left, top, right, bottom = self._content_margins
        inner = row_rect.adjusted(left, top, -right, -bottom)

        selected = option.state & QStyle.StateFlag.State_Selected
        focused = option.state & QStyle.StateFlag.State_HasFocus

        if selected:
            path = QPainterPath()
            path.addRoundedRect(QRectF(row_rect), self._CORNER_RADIUS, self._CORNER_RADIUS)
            gradient = QLinearGradient(QPointF(row_rect.left(), row_rect.top()), QPointF(row_rect.right(), row_rect.top()))
            start = QColor(ENTRY_FOCUS_START)
            if not focused:
                start.setAlpha(128)
            gradient.setColorAt(0.0, start)
            gradient.setColorAt(0.9, QColor(0x0A, 0x0E, 0x23, 0))
            gradient.setColorAt(1.0, Qt.GlobalColor.transparent)
            painter.fillPath(path, QBrush(gradient))

        display_name = (
            model.name.sort_name
            if self._name_display_strategy is NameDisplayStrategy.LIBRARY
            else model.name.name
        )

        title_font = _title_font()
        painter.setPen(QColor(TEXT_PRIMARY))
        text_right = inner.right()
        if focused:
            text_right -= _icon_block_width(model)
        text_width = max(0, text_right - inner.left())

        if model.name.alternative_name:
            alt_font = _alt_font()
            title_height = _wrapped_text_height(display_name, title_font, text_width)
            alt_height = _wrapped_text_height(model.name.alternative_name, alt_font, text_width)
            block_height = title_height + alt_height
            block_top = inner.top() + max(0, (inner.height() - block_height) // 2)

            title_rect = QRect(inner.left(), block_top, text_width, title_height)
            _draw_wrapped_text(painter, text=display_name, font=title_font, rect=title_rect)

            painter.setPen(QColor(TEXT_PRIMARY))
            alt_rect = QRect(inner.left(), block_top + title_height, text_width, alt_height)
            _draw_wrapped_text(painter, text=model.name.alternative_name, font=alt_font, rect=alt_rect)
        else:
            title_height = _wrapped_text_height(display_name, title_font, text_width)
            block_top = inner.top() + max(0, (inner.height() - title_height) // 2)
            title_rect = QRect(inner.left(), block_top, text_width, title_height)
            _draw_wrapped_text(painter, text=display_name, font=title_font, rect=title_rect)

        if focused:
            _paint_type_indicator(painter, inner, model)

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        model = index.data(Qt.ItemDataRole.UserRole)
        left, top, right, bottom = self._content_margins
        width = option.rect.width() if option.rect.width() > 0 else 800
        inner_width = max(1, width - left - right)
        if isinstance(model, ListEntryUiModel) and option.state & QStyle.StateFlag.State_HasFocus:
            inner_width = max(1, inner_width - _icon_block_width(model))

        title_metrics = QFontMetrics(_title_font())
        height = top + bottom + title_metrics.height()
        if isinstance(model, ListEntryUiModel):
            display_name = (
                model.name.sort_name
                if self._name_display_strategy is NameDisplayStrategy.LIBRARY
                else model.name.name
            )
            height = top + bottom + _wrapped_text_height(display_name, _title_font(), inner_width)
            if model.name.alternative_name:
                height += _wrapped_text_height(model.name.alternative_name, _alt_font(), inner_width)
            height += LIST_ROW_SPACING
        return QSize(width, height)


def _icon_block_width(model: ListEntryUiModel) -> int:
    icon_size = ICON_SIZE
    kind = model.entry_type.kind
    if kind is ListEntryTypeKind.SINGLE:
        return icon_size + ICON_GAP_MD
    count_font = QFont()
    count_font.setPixelSize(FONT_SIZE_COUNT)
    count_width = QFontMetrics(count_font).horizontalAdvance(str(model.entry_type.count))
    return icon_size + ICON_GAP_SM + count_width


def _entry_type_icon(kind: ListEntryTypeKind) -> IconKind:
    if kind is ListEntryTypeKind.SERIES:
        return IconKind.SERIES
    if kind is ListEntryTypeKind.GROUPING:
        return IconKind.FOLDER
    if kind is ListEntryTypeKind.PLAYABLES_GROUP:
        return IconKind.PLAYABLES
    return IconKind.PLAY_CIRCLE


def _paint_type_indicator(painter: QPainter, inner, model: ListEntryUiModel) -> None:
    kind = model.entry_type.kind
    color = QColor(TEXT_MUTED)
    icon_size = ICON_SIZE
    right = inner.right()
    icon_y = inner.top() + (inner.height() - icon_size) // 2

    if kind is ListEntryTypeKind.SINGLE:
        icon_rect = QRect(right - icon_size - ICON_GAP_MD, icon_y, icon_size, icon_size)
        paint_icon(painter, icon_rect, IconKind.PLAY_CIRCLE, color)
        return

    count_text = str(model.entry_type.count)
    count_font = QFont()
    count_font.setPixelSize(FONT_SIZE_COUNT)
    count_metrics = QFontMetrics(count_font)
    count_width = count_metrics.horizontalAdvance(count_text)

    icon_rect = QRect(right - count_width - ICON_GAP_SM - icon_size, icon_y, icon_size, icon_size)
    paint_icon(painter, icon_rect, _entry_type_icon(kind), color)

    painter.setFont(count_font)
    painter.setPen(color)
    count_rect = QRect(right - count_width, inner.top(), count_width, inner.height())
    painter.drawText(count_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, count_text)
