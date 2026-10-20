"""A fixed-height A3 row for one resumable video."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QFontMetrics, QPaintEvent, QPainter
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from lumi.ui.components.poster_widget import PosterWidget
from lumi.ui.poster_loader import PosterLoader

from lumi.domain.recent_watch import resume_timeline_percent
from lumi.ui.screens.recently_watched.controller import RecentWatchAction, RecentWatchRowUiModel
from lumi.ui.theme.typography import FONT_SIZE_LIST, FONT_SIZE_LIST_ALT, FONT_SIZE_XS
from lumi.ui.theme.spacing import (
    CORNER_RADIUS_SM,
    LIST_ROW_LEFT_INSET,
    LIST_ROW_RIGHT_INSET,
    LIST_ROW_VERTICAL_INSET,
    LIST_SELECTION_ACCENT_WIDTH,
    RECENT_WATCH_ACTION_BAND_HEIGHT,
    RECENT_WATCH_ACTION_GAP,
    RECENT_WATCH_BOTTOM_GAP,
    RECENT_WATCH_META_GAP,
    RECENT_WATCH_REMOVE_LEADING_GAP,
    RECENT_WATCH_SHOW_LINE_GAP,
    RECENT_WATCH_PROGRESS_HEIGHT,
    RECENT_WATCH_PROGRESS_MAX_WIDTH,
    RECENT_WATCH_ROW_GAP,
    RECENT_WATCH_THUMBNAIL_HEIGHT,
    RECENT_WATCH_THUMBNAIL_WIDTH,
)
from lumi.ui.theme.styles import apply_widget_stylesheet
from lumi.ui.theme.text_metrics import ink_single_line_height


class _ElidedLabel(QLabel):
    """A single text line that always elides rather than increasing row height."""

    def __init__(
        self,
        text: str = "",
        *,
        min_line_height_px: int | None = None,
        ink_pad_extra: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._min_line_height_px = min_line_height_px
        self._ink_pad_extra = ink_pad_extra
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(False)
        self.sync_line_height()

    def sync_line_height(self) -> None:
        metrics = QFontMetrics(self.font())
        ink_height = ink_single_line_height(metrics, self.text())
        if self._min_line_height_px is not None:
            ink_height = max(ink_height, self._min_line_height_px)
        self.setFixedHeight(ink_height + self._ink_pad_extra)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.FontChange:
            self.sync_line_height()
        super().changeEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.setFont(self.font())
        metrics = QFontMetrics(self.font())
        rect = self.contentsRect()
        text = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, max(1, rect.width()))
        alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        painter.drawText(rect, alignment, text)
        painter.end()


def _transparent_row_panel(widget: QWidget) -> None:
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    widget.setAutoFillBackground(False)


def _make_row_thumbnail() -> PosterWidget:
    poster = PosterWidget()
    poster.setObjectName("thumbnail")
    poster.set_corner_radius(CORNER_RADIUS_SM)
    poster.set_hero_fades_enabled(False)
    poster.setFixedSize(RECENT_WATCH_THUMBNAIL_WIDTH, RECENT_WATCH_THUMBNAIL_HEIGHT)
    return poster


class RecentWatchRow(QWidget):
    """A selectable play row whose action band never changes its geometry."""

    def __init__(self, model: RecentWatchRowUiModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RecentWatchRow")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self._model = model
        self._is_row_selected = False
        self._is_action_navigation_active = False
        self._selected_action_index = 0

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        row_height = RECENT_WATCH_THUMBNAIL_HEIGHT + 2 * LIST_ROW_VERTICAL_INSET
        self.setFixedHeight(row_height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._thumbnail = _make_row_thumbnail()
        self._thumbnail.set_poster_path(model.poster_path, immediate=True)

        playable_line_min = max(1, round(FONT_SIZE_LIST * 1.12))
        alt_line_min = max(1, round(FONT_SIZE_LIST_ALT * 1.2))
        self._playable = _ElidedLabel(
            model.playable_name,
            min_line_height_px=playable_line_min,
        )
        self._playable.setObjectName("playableName")
        self._show = _ElidedLabel(model.show_name or "", min_line_height_px=alt_line_min)
        self._show.setObjectName("showName")
        self._show.setVisible(model.show_name is not None)
        self._alternative = _ElidedLabel(
            model.alternative_name or "",
            min_line_height_px=alt_line_min,
        )
        self._alternative.setObjectName("alternativeName")
        self._alternative.setVisible(model.alternative_name is not None)

        self._show_meta = QWidget()
        self._show_meta.setObjectName("showMeta")
        _transparent_row_panel(self._show_meta)
        show_meta_layout = QVBoxLayout(self._show_meta)
        show_meta_layout.setContentsMargins(0, 0, 0, 0)
        show_meta_layout.setSpacing(RECENT_WATCH_SHOW_LINE_GAP)
        show_meta_layout.addWidget(self._show)
        show_meta_layout.addWidget(self._alternative)
        self._show_meta.setVisible(model.show_name is not None or model.alternative_name is not None)

        self._top = QWidget()
        self._top.setObjectName("top")
        _transparent_row_panel(self._top)
        top_layout = QVBoxLayout(self._top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(RECENT_WATCH_META_GAP)
        top_layout.addWidget(self._playable)
        if self._show_meta.isVisible():
            top_layout.addWidget(self._show_meta)

        when_line_min = max(1, round(FONT_SIZE_XS * 1.35))
        self._when = _ElidedLabel(
            _when_meta_line(model),
            min_line_height_px=when_line_min,
            ink_pad_extra=2,
        )
        self._when.setObjectName("when")
        self._progress = QProgressBar()
        self._progress.setObjectName("progress")
        self._progress.setRange(0, 1000)
        self._progress.setValue(round(model.progress_fraction * 1000))
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(RECENT_WATCH_PROGRESS_HEIGHT)
        self._progress.setMaximumWidth(RECENT_WATCH_PROGRESS_MAX_WIDTH)
        self._progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._action_band = QWidget()
        self._action_band.setObjectName("actionBand")
        _transparent_row_panel(self._action_band)
        self._action_band.setFixedHeight(RECENT_WATCH_ACTION_BAND_HEIGHT)
        action_layout = QHBoxLayout(self._action_band)
        action_layout.setContentsMargins(0, 2, 0, 0)
        action_layout.setSpacing(RECENT_WATCH_ACTION_GAP)
        self._action_widgets: list[QWidget] = []
        self._action_opacities: list[QGraphicsOpacityEffect] = []
        remove_widget: QLabel | None = None
        for action in model.actions:
            label = QLabel(_action_label(action, model.resume_action_label))
            label.setObjectName(
                "actionRemove" if action is RecentWatchAction.REMOVE else "actionLabel"
            )
            widget = label
            if action is RecentWatchAction.REMOVE:
                remove_widget = label
            opacity = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(opacity)
            self._action_widgets.append(widget)
            self._action_opacities.append(opacity)
            if action is not RecentWatchAction.REMOVE:
                action_layout.addWidget(widget)
        action_layout.addStretch(1)
        if remove_widget is not None:
            action_layout.addSpacing(RECENT_WATCH_REMOVE_LEADING_GAP)
            action_layout.addWidget(remove_widget)

        self._bottom = QWidget()
        self._bottom.setObjectName("bottom")
        _transparent_row_panel(self._bottom)
        bottom_layout = QVBoxLayout(self._bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(RECENT_WATCH_BOTTOM_GAP)
        bottom_layout.addWidget(self._when)
        bottom_layout.addWidget(self._progress)
        bottom_layout.addWidget(self._action_band)

        self._body = QWidget()
        self._body.setObjectName("body")
        _transparent_row_panel(self._body)
        self._body.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._body.setFixedHeight(RECENT_WATCH_THUMBNAIL_HEIGHT)
        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self._top)
        body_layout.addStretch(1)
        body_layout.addWidget(self._bottom)

        row_content_inset = LIST_ROW_LEFT_INSET + LIST_SELECTION_ACCENT_WIDTH
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            row_content_inset,
            LIST_ROW_VERTICAL_INSET,
            LIST_ROW_RIGHT_INSET,
            LIST_ROW_VERTICAL_INSET,
        )
        layout.setSpacing(RECENT_WATCH_ROW_GAP)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._thumbnail)
        layout.addWidget(self._body, stretch=1)

        self.ensurePolished()
        for label in (self._playable, self._show, self._alternative, self._when):
            label.ensurePolished()
            if isinstance(label, _ElidedLabel):
                label.sync_line_height()
        self._sync_row_chrome()

    @property
    def model(self) -> RecentWatchRowUiModel:
        return self._model

    @property
    def selected_action(self) -> RecentWatchAction:
        return self._model.actions[self._selected_action_index]

    @property
    def thumbnail_presentation_state(self) -> str:
        return self._thumbnail.presentation_state

    @property
    def thumbnail_size(self) -> QSize:
        return self._thumbnail.size()

    @property
    def play_badge_visible(self) -> bool:
        return self._thumbnail.play_badge_visible

    def bind_poster_loader(self, loader: PosterLoader) -> None:
        self._thumbnail.bind_loader(loader)
        self._thumbnail.set_poster_path(self._model.poster_path, immediate=True)

    def set_row_selected(self, selected: bool) -> None:
        if self._is_row_selected == selected:
            return
        self._is_row_selected = selected
        self._sync_row_chrome()

    def set_action_navigation_active(self, active: bool) -> None:
        if self._is_action_navigation_active == active:
            return
        self._is_action_navigation_active = active
        self._sync_row_chrome()

    def move_action(self, delta: int) -> None:
        next_index = max(
            0,
            min(len(self._model.actions) - 1, self._selected_action_index + delta),
        )
        if self._selected_action_index == next_index:
            return
        self._selected_action_index = next_index
        self._sync_row_chrome()

    def activate_selected_action(self) -> None:
        self._model.activate(self.selected_action)

    def _sync_row_chrome(self) -> None:
        self._thumbnail.set_play_badge_visible(self._is_row_selected)
        for index, (widget, opacity) in enumerate(
            zip(self._action_widgets, self._action_opacities, strict=True)
        ):
            labels_visible = self._is_row_selected
            opacity.setOpacity(1.0 if labels_visible else 0.0)
            widget.setProperty(
                "actionSelected",
                labels_visible
                and self._is_action_navigation_active
                and index == self._selected_action_index,
            )
            if isinstance(widget, QLabel):
                widget.style().unpolish(widget)
                widget.style().polish(widget)


def _action_label(action: RecentWatchAction, resume_label: str) -> str:
    if action is RecentWatchAction.EPISODES:
        return "Episodes"
    if action is RecentWatchAction.REMOVE:
        return "Remove"
    return resume_label


def _when_meta_line(model: RecentWatchRowUiModel) -> str:
    """Prototype play row: ``recent-row__when`` is ``{when} · {pct}%`` (timeline bookmark)."""
    percent = resume_timeline_percent(
        model.resume_position_seconds,
        model.media_duration_seconds,
    )
    if percent is None:
        return model.played_at_label
    return f"{model.played_at_label} · {percent}%"
