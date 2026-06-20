"""Fullscreen player overlay hosted inside the main window."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import isValid

from lumi.ui.player.render.video_area import VideoArea


class PlayerHost(QWidget):
    """Covers the main window while a video is playing."""

    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setVisible(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._focus_before_play: QWidget | None = None
        self._video_area = VideoArea(on_close=self._request_close, parent=self)

    def play(self, uri: str, library_path: PurePosixPath) -> None:
        self._focus_before_play = QApplication.focusWidget()
        parent = self.parentWidget()
        self.setGeometry(parent.rect() if parent is not None else self.rect())
        self._video_area.setGeometry(self.rect())
        self.show()
        self.raise_()
        self._video_area.mpv_widget.show()
        QApplication.processEvents()
        self._video_area.play_file(uri, library_path)
        self.grabKeyboard()
        self.activateWindow()
        self.setFocus()
        self._video_area.setFocus()

    def close_player(self) -> None:
        saved_focus = self._focus_before_play
        self._focus_before_play = None
        self.releaseKeyboard()
        self._video_area.stop()
        self.hide()
        QTimer.singleShot(0, lambda: self._restore_focus(saved_focus))

    def _restore_focus(self, saved_focus: QWidget | None) -> None:
        if saved_focus is not None and isValid(saved_focus) and saved_focus.isVisible():
            saved_focus.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        parent = self.parentWidget()
        if parent is not None and hasattr(parent, "restore_screen_focus"):
            parent.restore_screen_focus()

    def shutdown(self) -> None:
        self._video_area.shutdown()

    def is_playing(self) -> bool:
        return self.isVisible()

    def _request_close(self) -> None:
        self.close_player()
        self.close_requested.emit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._video_area.setGeometry(self.rect())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.StandardKey.Quit):
            parent = self.parentWidget()
            if parent is not None:
                parent.close()
            else:
                app = QApplication.instance()
                if app is not None:
                    app.quit()
            event.accept()
            return
        self._video_area.forward_key_event(event)
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self._video_area.forward_key_release_event(event)
        event.accept()
