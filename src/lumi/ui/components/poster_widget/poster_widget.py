"""Poster preview widget — crop fill with edge gradient."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from lumi.domain.poster.image_file_poster_provider import is_placeholder_poster_path
from lumi.ui.poster_loader import PosterLoader, normalize_poster_pixmap
from lumi.ui.theme.colors import BACKGROUND
from lumi.ui.theme.styles import apply_widget_stylesheet


class PosterWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PosterWidget")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._loader: PosterLoader | None = None
        self._current_path: PurePosixPath | None = None
        self._pixmap: QPixmap | None = None
        self._placeholder_text = "No poster"
        self._state = "empty"

        self._label = QLabel("No poster")
        self._label.setObjectName("placeholder")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

    def bind_loader(self, loader: PosterLoader) -> None:
        if self._loader is loader:
            return
        if self._loader is not None:
            self._loader.loaded.disconnect(self._on_loaded)
            self._loader.failed.disconnect(self._on_failed)
            self._loader.cleared.disconnect(self._on_cleared)
        self._loader = loader
        loader.loaded.connect(self._on_loaded)
        loader.failed.connect(self._on_failed)
        loader.cleared.connect(self._on_cleared)
        if self._current_path is not None:
            loader.load(self._current_path)

    def set_poster_path(self, poster_path: PurePosixPath | None) -> None:
        self._current_path = poster_path
        if poster_path is None:
            if self._loader is not None:
                self._loader.load(None)
            else:
                self._show_empty()
            return

        if is_placeholder_poster_path(poster_path):
            self._show_empty()
            return

        if self._loader is not None:
            if self._loader.load(poster_path):
                return
            self._show_loading()
            return

        self._show_empty()

    def set_loading(self) -> None:
        self._show_loading()

    def set_error(self, message: str = "No poster") -> None:
        self._pixmap = None
        self._state = "error"
        self._placeholder_text = message
        self._label.show()
        self._apply_label_state()
        self.update()

    def set_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        self._pixmap = normalize_poster_pixmap(pixmap)
        self._state = "loaded"
        self._label.hide()
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._pixmap is not None:
            self.update()

    def paintEvent(self, event) -> None:
        if self._pixmap is not None and not self._pixmap.isNull():
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(BACKGROUND))

            target = self.rect()
            scaled = self._pixmap.scaled(
                target.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = target.x() + (target.width() - scaled.width()) // 2
            y = target.y()
            painter.drawPixmap(x, y, scaled)

            gradient = QLinearGradient(target.left(), 0, target.right(), 0)
            gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
            gradient.setColorAt(1.0, QColor(BACKGROUND))
            painter.fillRect(target, gradient)
            painter.end()
            return

        super().paintEvent(event)

    def _show_empty(self) -> None:
        self._pixmap = None
        self._state = "empty"
        self._placeholder_text = "No poster"
        self._label.show()
        self._apply_label_state()
        self.update()

    def _show_loading(self) -> None:
        self._pixmap = None
        self._state = "loading"
        self._label.hide()
        self.update()

    def _apply_label_state(self) -> None:
        self._label.setText(self._placeholder_text)
        self._label.setProperty("state", self._state)
        self._label.style().unpolish(self._label)
        self._label.style().polish(self._label)

    def _on_loaded(self, poster_path: PurePosixPath, pixmap: QPixmap) -> None:
        if poster_path != self._current_path:
            return
        self.set_pixmap(pixmap)

    def _on_failed(self, poster_path: PurePosixPath, message: str) -> None:
        del message
        if poster_path != self._current_path:
            return
        self.set_error("No poster")

    def _on_cleared(self) -> None:
        self._show_empty()
