"""Screen header with breadcrumbs and tags."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from lumi.ui.theme.colors import ALPHABET_ACTIVE_TINT, TOPBAR_ACTIVE
from lumi.ui.theme.spacing import (
    HEADER_TAG_GAP,
    HEADER_TAG_PAD_H,
    HEADER_TAG_PAD_V,
    HEADER_TAG_ROW_MARGIN_V,
    LIST_ROW_LEFT_INSET,
    SPACE_SM,
)
from lumi.ui.theme.styles import apply_widget_stylesheet
from lumi.ui.theme.text_metrics import ink_single_line_height, ink_text_width
from lumi.ui.theme.typography import FONT_SIZE_XS


class _TagChip(QWidget):
    """Compact accent-dim tag pill (series header, matches prototype)."""

    _PAD_H = HEADER_TAG_PAD_H
    _PAD_V = HEADER_TAG_PAD_V
    _ROW_MARGIN_V = HEADER_TAG_ROW_MARGIN_V

    def __init__(self, tag: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tag = tag
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def _font(self) -> QFont:
        font = QFont()
        font.setPixelSize(FONT_SIZE_XS)
        return font

    def sizeHint(self) -> QSize:
        metrics = QFontMetrics(self._font())
        text_width = ink_text_width(metrics, self._tag)
        width = self._PAD_H * 2 + text_width
        height = ink_single_line_height(metrics, self._tag) + self._PAD_V * 2 + self._ROW_MARGIN_V * 2
        return QSize(width, height)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        del event
        metrics = QFontMetrics(self._font())
        inner_height = ink_single_line_height(metrics, self._tag) + self._PAD_V * 2
        pill_y = self._ROW_MARGIN_V
        pill_rect = QRectF(0, pill_y, self.width(), inner_height)
        radius = inner_height / 2

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(ALPHABET_ACTIVE_TINT))
        painter.drawRoundedRect(pill_rect, radius, radius)
        painter.setFont(self._font())
        painter.setPen(QColor(TOPBAR_ACTIVE))
        painter.drawText(
            pill_rect,
            Qt.AlignmentFlag.AlignCenter,
            self._tag,
        )
        painter.end()


class Header(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Header")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))

        self._breadcrumbs = QLabel()
        self._breadcrumbs.setObjectName("breadcrumbs")
        self._title = QLabel()
        self._title.setObjectName("title")
        self._title.setWordWrap(True)
        self._subtitle = QLabel()
        self._subtitle.setObjectName("subtitle")
        self._subtitle.setWordWrap(True)
        self._tags_container = QWidget()
        self._tags_layout = QHBoxLayout(self._tags_container)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(HEADER_TAG_GAP)

        text_block = QWidget()
        text_block_layout = QVBoxLayout(text_block)
        text_block_layout.setContentsMargins(0, 0, 0, 0)
        text_block_layout.setSpacing(0)
        text_block_layout.addWidget(self._breadcrumbs)
        text_block_layout.addSpacing(SPACE_SM)
        text_block_layout.addWidget(self._title)
        text_block_layout.addWidget(self._subtitle)
        text_block_layout.addWidget(self._tags_container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(LIST_ROW_LEFT_INSET, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(text_block)

    def set_content(
        self,
        *,
        breadcrumbs: str,
        title: str,
        subtitle: str | None = None,
        tags: frozenset[str] | set[str] | None = None,
    ) -> None:
        self._breadcrumbs.setText(breadcrumbs)
        self._title.setText(title)
        if subtitle:
            self._subtitle.setText(subtitle)
            self._subtitle.show()
        else:
            self._subtitle.hide()

        while self._tags_layout.count():
            item = self._tags_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        tag_values = sorted(tags or [])
        if tag_values:
            self._tags_container.show()
            for tag in tag_values:
                self._tags_layout.addWidget(_TagChip(tag), alignment=Qt.AlignmentFlag.AlignLeft)
            self._tags_layout.addStretch()
        else:
            self._tags_container.hide()
