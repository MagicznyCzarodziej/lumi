"""Video compositor: mpv widget + overlay."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QWidget

from lumi.ui.player.controller.controller import MpvController
from lumi.ui.player.overlay.input_router import is_dismiss_key
from lumi.ui.player.overlay.overlay import PlayerOverlay
from lumi.ui.player.render.mpv_widget import MpvWidget


class VideoArea(QWidget):
    def __init__(
        self,
        *,
        on_close: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumSize(960, 540)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.mpv_widget = MpvWidget(self)
        self.mpv_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mpv_widget.installEventFilter(self)
        self.controller = MpvController(lambda: self.mpv_widget.mpv)
        self.overlay = PlayerOverlay(self.controller, on_close=on_close, parent=self)
        self.overlay.raise_()
        self.overlay.bind()
        self.mpv_widget.render_update.connect(
            self.overlay.notify_repaint_tick,
            Qt.ConnectionType.QueuedConnection,
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        rect = self.rect()
        self.mpv_widget.setGeometry(rect)
        self.overlay.setGeometry(rect)
        if self.overlay.isVisible():
            self.overlay.raise_()

    def play_file(self, path: str) -> None:
        self.mpv_widget.show()
        self.mpv_widget.raise_()
        self.mpv_widget.play_file(path)
        self.overlay.set_media_info(path)
        self.overlay.start_watching()
        QApplication.processEvents()
        self.setFocus()

    def stop(self) -> None:
        self.mpv_widget.stop()

    def shutdown(self) -> None:
        self.overlay.unbind()
        self.mpv_widget.shutdown()

    def forward_key_event(self, event: QKeyEvent) -> None:
        if is_dismiss_key(event.key()) and self.overlay.close_if_watching():
            return
        self.overlay.keyPressEvent(event)

    def forward_key_release_event(self, event: QKeyEvent) -> None:
        scrub = self.overlay.state.scrub
        if scrub is not None and scrub.keyboard_scrubbing:
            self.overlay.keyReleaseEvent(event)
            return
        if not self.overlay.isVisible():
            return
        self.overlay.keyReleaseEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if watched is not self.mpv_widget:
            return super().eventFilter(watched, event)

        event_type = event.type()
        if event_type == QEvent.Type.KeyPress:
            self.forward_key_event(event)
            return True
        if event_type == QEvent.Type.KeyRelease:
            self.forward_key_release_event(event)
            return True
        if event_type == QEvent.Type.MouseMove:
            if not self.overlay.isVisible():
                self.overlay.show_controls()
            return True
        if event_type == QEvent.Type.MouseButtonPress:
            if not self.overlay.isVisible():
                self.overlay.show_controls()
            self.overlay.mousePressEvent(event)
            return True
        if event_type == QEvent.Type.MouseButtonRelease:
            self.overlay.mouseReleaseEvent(event)
            return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.forward_key_event(event)
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self.forward_key_release_event(event)
        event.accept()
