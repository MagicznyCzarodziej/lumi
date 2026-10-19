"""Gradient list row delegate."""

from __future__ import annotations

from math import ceil

from PySide6.QtCore import QElapsedTimer, QPersistentModelIndex, QRect, Qt, QSize, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QImage, QLinearGradient, QPainter
from PySide6.QtWidgets import QAbstractItemView, QStyledItemDelegate, QStyle, QStyleOptionViewItem, QWidget

from lumi.ui.components.list_entry import ListEntryTypeKind, ListEntryUiModel, NameDisplayStrategy
from lumi.ui.icons.material_icons import IconKind, paint_icon
from lumi.ui.theme.colors import (
    LIST_SELECTION_ACCENT,
    LIST_SELECTION_TINT,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from lumi.ui.theme.motion import (
    FOCUS_POP_DURATION_MS,
    FOCUS_POP_FRAME_INTERVAL_MS,
    focus_pop_highlight_color,
    focus_pop_scale,
)
from lumi.ui.theme.scale import scaled as s
from lumi.ui.theme.spacing import (
    CORNER_RADIUS_SM,
    LIST_ROW_LINE_GAP,
    LIST_ROW_MARGINS,
    LIST_ROW_SPACING,
    LIST_SELECTION_ACCENT_WIDTH,
    LIST_TYPE_INDICATOR_GAP,
    LIST_TYPE_INDICATOR_ICON_SIZE,
    LIST_TYPE_INDICATOR_TEXT_GAP,
)
from lumi.ui.theme.text_metrics import ink_single_line_height, ink_text_width
from lumi.ui.theme.typography import FONT_SIZE_COUNT, FONT_SIZE_LIST, FONT_SIZE_LIST_ALT

_MARQUEE_FRAME_INTERVAL_MS = 33
_MARQUEE_START_DELAY_MS = 900
_MARQUEE_END_DELAY_MS = 700
_MARQUEE_SPEED_PX_PER_SECOND = s(40)
_TEXT_FADE_WIDTH = s(14)


def _title_font() -> QFont:
    font = QFont()
    font.setPixelSize(FONT_SIZE_LIST)
    font.setWeight(QFont.Weight.Medium)
    return font


def _alt_font() -> QFont:
    font = QFont()
    font.setPixelSize(FONT_SIZE_LIST_ALT)
    return font


def _single_line_height(text: str, font: QFont) -> int:
    return ink_single_line_height(QFontMetrics(font), text)


def _text_baseline(rect: QRect, metrics: QFontMetrics) -> int:
    return rect.top() + max(0, (rect.height() - metrics.height()) // 2) + metrics.ascent()


def _draw_faded_text(
    painter: QPainter,
    *,
    text: str,
    font: QFont,
    rect: QRect,
    x_positions: tuple[int, ...],
    fade_left: bool,
    fade_right: bool,
) -> None:
    if not text or rect.width() <= 0 or rect.height() <= 0:
        return

    device = painter.device()
    device_pixel_ratio = device.devicePixelRatioF() if device is not None else 1.0
    image = QImage(
        max(1, ceil(rect.width() * device_pixel_ratio)),
        max(1, ceil(rect.height() * device_pixel_ratio)),
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.setDevicePixelRatio(device_pixel_ratio)
    image.fill(Qt.GlobalColor.transparent)

    layer = QPainter(image)
    layer.setRenderHints(painter.renderHints())
    layer.setFont(font)
    layer.setPen(painter.pen())
    metrics = QFontMetrics(font)
    local_rect = QRect(0, 0, rect.width(), rect.height())
    baseline = _text_baseline(local_rect, metrics)
    for x in x_positions:
        layer.drawText(x, baseline, text)

    fade_width = min(_TEXT_FADE_WIDTH, max(1, rect.width() // 2))
    fade_ratio = fade_width / rect.width()
    solid = QColor(255, 255, 255)
    transparent = QColor(255, 255, 255, 0)
    mask = QLinearGradient(0, 0, rect.width(), 0)
    mask.setColorAt(0.0, transparent if fade_left else solid)
    if fade_left:
        mask.setColorAt(fade_ratio, solid)
    if fade_right:
        mask.setColorAt(1.0 - fade_ratio, solid)
    mask.setColorAt(1.0, transparent if fade_right else solid)

    layer.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    layer.fillRect(local_rect, QBrush(mask))
    layer.end()
    painter.drawImage(rect.topLeft(), image)


def _draw_elided_text(
    painter: QPainter,
    *,
    text: str,
    font: QFont,
    rect: QRect,
) -> None:
    if not text or rect.width() <= 0:
        return
    painter.setFont(font)
    metrics = QFontMetrics(font)
    overflows = ink_text_width(metrics, text) > rect.width()
    visible_text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, rect.width())
    if overflows:
        _draw_faded_text(
            painter,
            text=visible_text,
            font=font,
            rect=rect,
            x_positions=(0,),
            fade_left=False,
            fade_right=True,
        )
        return

    painter.save()
    painter.setClipRect(rect, Qt.ClipOperation.IntersectClip)
    painter.drawText(rect.left(), _text_baseline(rect, metrics), visible_text)
    painter.restore()


def _draw_marquee_text(
    painter: QPainter,
    *,
    text: str,
    font: QFont,
    rect: QRect,
    offset: int,
    max_offset: int,
) -> None:
    if not text or rect.width() <= 0:
        return
    _draw_faded_text(
        painter,
        text=text,
        font=font,
        rect=rect,
        x_positions=(-offset,),
        fade_left=offset > 0,
        fade_right=offset < max_offset,
    )


def _marquee_offset(elapsed_ms: int, travel_distance: int) -> int:
    if elapsed_ms <= _MARQUEE_START_DELAY_MS or travel_distance <= 0:
        return 0
    travel_duration_ms = max(
        1,
        ceil(travel_distance * 1000 / _MARQUEE_SPEED_PX_PER_SECOND),
    )
    cycle_duration_ms = (
        _MARQUEE_START_DELAY_MS
        + travel_duration_ms
        + _MARQUEE_END_DELAY_MS
        + travel_duration_ms
    )
    cycle_position_ms = elapsed_ms % cycle_duration_ms
    if cycle_position_ms <= _MARQUEE_START_DELAY_MS:
        return 0
    cycle_position_ms -= _MARQUEE_START_DELAY_MS

    if cycle_position_ms < travel_duration_ms:
        return cycle_position_ms * travel_distance // travel_duration_ms
    cycle_position_ms -= travel_duration_ms

    if cycle_position_ms <= _MARQUEE_END_DELAY_MS:
        return travel_distance
    cycle_position_ms -= _MARQUEE_END_DELAY_MS

    if cycle_position_ms < travel_duration_ms:
        return travel_distance - cycle_position_ms * travel_distance // travel_duration_ms
    return 0


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
        self._marquee_index = QPersistentModelIndex()
        self._marquee_text = ""
        self._marquee_clock = QElapsedTimer()
        self._marquee_timer = QTimer(self)
        self._marquee_timer.setInterval(_MARQUEE_FRAME_INTERVAL_MS)
        self._marquee_timer.timeout.connect(self._update_marquee)
        self._pop_index = QPersistentModelIndex()
        self._pop_clock = QElapsedTimer()
        self._pop_timer = QTimer(self)
        self._pop_timer.setInterval(FOCUS_POP_FRAME_INTERVAL_MS)
        self._pop_timer.timeout.connect(self._update_pop)

    @property
    def content_margins(self) -> tuple[int, int, int, int]:
        """Insets from a row edge to its text and type-indicator content."""
        return self._content_margins

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        model = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(model, ListEntryUiModel):
            super().paint(painter, option, index)
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(option.rect)
        pop_progress = self._pop_progress_for(index)
        pop_scale = focus_pop_scale(pop_progress) if pop_progress is not None else 1.0
        if pop_scale != 1.0:
            center = option.rect.center()
            painter.translate(center.x(), center.y())
            painter.scale(pop_scale, pop_scale)
            painter.translate(-center.x(), -center.y())

        outer = option.rect
        row_rect = outer.adjusted(0, 0, 0, -LIST_ROW_SPACING)
        left, top, right, bottom = self._content_margins
        inner = row_rect.adjusted(left, top, -right, -bottom)

        selected = option.state & QStyle.StateFlag.State_Selected
        focused = option.state & QStyle.StateFlag.State_HasFocus

        if selected:
            painter.fillRect(
                row_rect,
                focus_pop_highlight_color(QColor(LIST_SELECTION_TINT), pop_progress),
            )
            painter.fillRect(
                row_rect.left(),
                row_rect.top(),
                LIST_SELECTION_ACCENT_WIDTH,
                row_rect.height(),
                focus_pop_highlight_color(QColor(LIST_SELECTION_ACCENT), pop_progress),
            )

        display_name = (
            model.name.sort_name
            if self._name_display_strategy is NameDisplayStrategy.LIBRARY
            else model.name.name
        )

        title_font = _title_font()
        title_metrics = QFontMetrics(title_font)
        painter.setPen(QColor(TEXT_PRIMARY))
        show_type_meta = selected and focused
        text_right = inner.right()
        if show_type_meta:
            text_right -= _icon_block_width(model) + LIST_TYPE_INDICATOR_TEXT_GAP
        text_width = max(0, text_right - inner.left())

        title_height = _single_line_height(display_name, title_font)
        if model.name.alternative_name:
            alt_font = _alt_font()
            alt_height = _single_line_height(model.name.alternative_name, alt_font)
            block_height = title_height + LIST_ROW_LINE_GAP + alt_height
            block_top = inner.top() + max(0, (inner.height() - block_height) // 2)

            title_rect = QRect(inner.left(), block_top, text_width, title_height)
            alt_rect = QRect(
                inner.left(),
                block_top + title_height + LIST_ROW_LINE_GAP,
                text_width,
                alt_height,
            )
        else:
            block_top = inner.top() + max(0, (inner.height() - title_height) // 2)
            title_rect = QRect(inner.left(), block_top, text_width, title_height)
            alt_font = None
            alt_rect = None

        title_overflows = ink_text_width(title_metrics, display_name) > text_width
        marquee_active = bool(selected and focused and title_overflows)
        if marquee_active:
            self._start_marquee(index, display_name)
            travel_distance = max(1, ink_text_width(title_metrics, display_name) - text_width)
            _draw_marquee_text(
                painter,
                text=display_name,
                font=title_font,
                rect=title_rect,
                offset=_marquee_offset(self._marquee_clock.elapsed(), travel_distance),
                max_offset=travel_distance,
            )
        else:
            self._stop_marquee_for(index)
            _draw_elided_text(painter, text=display_name, font=title_font, rect=title_rect)

        if alt_font is not None and alt_rect is not None:
            painter.setPen(QColor(TEXT_MUTED))
            _draw_elided_text(
                painter,
                text=model.name.alternative_name or "",
                font=alt_font,
                rect=alt_rect,
            )

        if show_type_meta:
            _paint_type_indicator(painter, inner, model)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        model = index.data(Qt.ItemDataRole.UserRole)
        _left, top, _right, bottom = self._content_margins
        width = option.rect.width() if option.rect.width() > 0 else 800

        title_metrics = QFontMetrics(_title_font())
        height = top + bottom + title_metrics.height()
        if isinstance(model, ListEntryUiModel):
            display_name = (
                model.name.sort_name
                if self._name_display_strategy is NameDisplayStrategy.LIBRARY
                else model.name.name
            )
            height = top + bottom + _single_line_height(display_name, _title_font())
            if model.name.alternative_name:
                height += (
                    LIST_ROW_LINE_GAP
                    + _single_line_height(model.name.alternative_name, _alt_font())
                )
            height += LIST_ROW_SPACING
        return QSize(width, height)

    def _start_marquee(self, index, text: str) -> None:
        persistent_index = QPersistentModelIndex(index)
        if self._marquee_index != persistent_index or self._marquee_text != text:
            self._marquee_index = persistent_index
            self._marquee_text = text
            self._marquee_clock.restart()
        if not self._marquee_timer.isActive():
            self._marquee_timer.start()

    def _stop_marquee_for(self, index) -> None:
        if self._marquee_index == QPersistentModelIndex(index):
            self._stop_marquee()

    def _stop_marquee(self) -> None:
        self._marquee_timer.stop()
        self._marquee_index = QPersistentModelIndex()
        self._marquee_text = ""
        self._marquee_clock.invalidate()

    def _update_marquee(self) -> None:
        if not self._marquee_index.isValid():
            self._stop_marquee()
            return
        parent = self.parent()
        if isinstance(parent, QAbstractItemView):
            if not parent.isVisible() or not parent.hasFocus():
                self._stop_marquee()
                return
            parent.viewport().update(parent.visualRect(self._marquee_index))

    def start_pop(self, index) -> None:
        if not index.isValid():
            return
        self._pop_index = QPersistentModelIndex(index)
        self._pop_clock.restart()
        self._pop_timer.start()
        self._update_pop()

    def _pop_progress_for(self, index) -> float | None:
        if self._pop_index != QPersistentModelIndex(index):
            return None
        elapsed_ms = self._pop_clock.elapsed()
        if elapsed_ms >= FOCUS_POP_DURATION_MS:
            self._stop_pop()
            return None
        return elapsed_ms / FOCUS_POP_DURATION_MS

    def _stop_pop(self) -> None:
        self._pop_timer.stop()
        self._pop_index = QPersistentModelIndex()
        self._pop_clock.invalidate()

    def _update_pop(self) -> None:
        if not self._pop_index.isValid():
            self._stop_pop()
            return
        parent = self.parent()
        if isinstance(parent, QAbstractItemView):
            if not parent.isVisible() or not parent.hasFocus():
                self._stop_pop()
                return
            parent.viewport().update(parent.visualRect(self._pop_index))


def _icon_block_width(model: ListEntryUiModel) -> int:
    icon_size = LIST_TYPE_INDICATOR_ICON_SIZE
    kind = model.entry_type.kind
    if kind is ListEntryTypeKind.SINGLE:
        return icon_size
    count_font = QFont()
    count_font.setPixelSize(FONT_SIZE_COUNT)
    count_width = QFontMetrics(count_font).horizontalAdvance(str(model.entry_type.count))
    return icon_size + LIST_TYPE_INDICATOR_GAP + count_width


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
    icon_size = LIST_TYPE_INDICATOR_ICON_SIZE
    right = inner.right()
    icon_y = inner.top() + (inner.height() - icon_size) // 2

    if kind is ListEntryTypeKind.SINGLE:
        icon_rect = QRect(right - icon_size, icon_y, icon_size, icon_size)
        paint_icon(painter, icon_rect, IconKind.PLAY_CIRCLE, color)
        return

    count_text = str(model.entry_type.count)
    count_font = QFont()
    count_font.setPixelSize(FONT_SIZE_COUNT)
    count_metrics = QFontMetrics(count_font)
    count_width = count_metrics.horizontalAdvance(count_text)

    icon_rect = QRect(
        right - count_width - LIST_TYPE_INDICATOR_GAP - icon_size,
        icon_y,
        icon_size,
        icon_size,
    )
    paint_icon(painter, icon_rect, _entry_type_icon(kind), color)

    painter.setFont(count_font)
    painter.setPen(color)
    count_rect = QRect(right - count_width, inner.top(), count_width, inner.height())
    painter.drawText(count_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, count_text)
