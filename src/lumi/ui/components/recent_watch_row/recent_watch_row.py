"""A fixed-height A3 row for one resumable video."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontMetrics, QPaintEvent, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget

from lumi.ui.screens.recently_watched.controller import RecentWatchAction, RecentWatchRowUiModel
from lumi.ui.theme.colors import LIST_SELECTION_ACCENT, LIST_SELECTION_TINT
from lumi.ui.theme.spacing import (
    RECENT_WATCH_ACTION_BAND_HEIGHT,
    RECENT_WATCH_PROGRESS_HEIGHT,
    RECENT_WATCH_ROW_GAP,
    RECENT_WATCH_THUMBNAIL_HEIGHT,
    RECENT_WATCH_THUMBNAIL_WIDTH,
    LIST_SELECTION_ACCENT_WIDTH,
    SPACE_SM,
)
from lumi.ui.theme.styles import apply_widget_stylesheet


class _ElidedLabel(QLabel):
    """A single text line that always elides rather than increasing row height."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.setFont(self.font())
        metrics = QFontMetrics(self.font())
        text = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, self.contentsRect().width())
        painter.drawText(
            self.contentsRect(),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            text,
        )
        painter.end()


class RecentWatchRow(QWidget):
    """A selectable play row whose action band never changes its geometry."""

    def __init__(self, model: RecentWatchRowUiModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RecentWatchRow")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self._model = model
        self._is_row_focused = False
        self._selected_action_index = 0

        self.setFixedHeight(RECENT_WATCH_THUMBNAIL_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._thumbnail = QFrame()
        self._thumbnail.setObjectName("thumbnail")
        self._thumbnail.setFixedSize(
            RECENT_WATCH_THUMBNAIL_WIDTH,
            RECENT_WATCH_THUMBNAIL_HEIGHT,
        )
        self._thumbnail.setToolTip(
            model.poster_path.as_posix() if model.poster_path is not None else ""
        )

        self._playable = _ElidedLabel(model.playable_name)
        self._playable.setObjectName("playableName")
        self._show = _ElidedLabel(model.show_name or "")
        self._show.setObjectName("showName")
        self._show.setVisible(model.show_name is not None)
        self._alternative = _ElidedLabel(model.alternative_name or "")
        self._alternative.setObjectName("alternativeName")
        self._alternative.setVisible(model.alternative_name is not None)

        self._time = QLabel(model.time_label)
        self._time.setObjectName("time")
        self._progress = QProgressBar()
        self._progress.setObjectName("progress")
        self._progress.setRange(0, 1000)
        self._progress.setValue(round(model.progress_fraction * 1000))
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(RECENT_WATCH_PROGRESS_HEIGHT)

        self._action_band = QWidget()
        self._action_band.setObjectName("actionBand")
        self._action_band.setFixedHeight(RECENT_WATCH_ACTION_BAND_HEIGHT)
        action_layout = QHBoxLayout(self._action_band)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(SPACE_SM)
        self._action_labels: list[QLabel] = []
        for action in model.actions:
            label = QLabel(_action_label(action))
            label.setObjectName("actionLabel")
            action_layout.addWidget(label)
            self._action_labels.append(label)
        action_layout.addStretch(1)

        body = QWidget()
        body.setObjectName("body")
        body.setFixedHeight(RECENT_WATCH_THUMBNAIL_HEIGHT)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self._playable)
        body_layout.addWidget(self._show)
        body_layout.addWidget(self._alternative)
        body_layout.addStretch(1)
        body_layout.addWidget(self._time)
        body_layout.addSpacing(SPACE_SM)
        body_layout.addWidget(self._progress)
        body_layout.addSpacing(SPACE_SM)
        body_layout.addWidget(self._action_band)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(RECENT_WATCH_ROW_GAP)
        layout.addWidget(self._thumbnail)
        layout.addWidget(body, stretch=1)

        self._sync_action_band()

    @property
    def model(self) -> RecentWatchRowUiModel:
        return self._model

    @property
    def selected_action(self) -> RecentWatchAction:
        return self._model.actions[self._selected_action_index]

    def set_row_focused(self, focused: bool) -> None:
        if self._is_row_focused == focused:
            return
        self._is_row_focused = focused
        self.setProperty("rowFocused", focused)
        self.style().unpolish(self)
        self.style().polish(self)
        self._sync_action_band()

    def move_action(self, delta: int) -> None:
        next_index = max(
            0,
            min(len(self._model.actions) - 1, self._selected_action_index + delta),
        )
        if self._selected_action_index == next_index:
            return
        self._selected_action_index = next_index
        self._sync_action_band()

    def activate_selected_action(self) -> None:
        self._model.activate(self.selected_action)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self._is_row_focused:
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(LIST_SELECTION_TINT))
        painter.fillRect(
            0,
            0,
            LIST_SELECTION_ACCENT_WIDTH,
            self.height(),
            QColor(LIST_SELECTION_ACCENT),
        )
        painter.end()

    def _sync_action_band(self) -> None:
        for index, label in enumerate(self._action_labels):
            visible = self._is_row_focused
            label.setVisible(visible)
            label.setProperty(
                "actionSelected",
                visible and index == self._selected_action_index,
            )
            label.style().unpolish(label)
            label.style().polish(label)


def _action_label(action: RecentWatchAction) -> str:
    if action is RecentWatchAction.EPISODES:
        return "Episodes"
    return "Resume"
