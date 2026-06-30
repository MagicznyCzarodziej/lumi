"""Fullscreen player overlay hosted inside the main window."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import isValid

from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.file_writer import FileWriter
from lumi.domain.filesystem.files_lister import FilesLister
from lumi.domain.filesystem.video_range_reader import VideoRangeReader
from lumi.domain.library.library_repository import LibraryRepository
from lumi.domain.playback import PlaybackUriResolver
from lumi.domain.power.sleep_inhibitor import SleepInhibitor
from lumi.domain.subtitles.cache import SubtitleCache
from lumi.domain.subtitles.provider import SubtitleDownloadProvider
from lumi.domain.subtitles.saved_state import NapiSavedStateStore
from lumi.ui.player.render.video_area import VideoArea


class PlayerHost(QWidget):
    """Covers the main window while a video is playing."""

    close_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        files_lister: FilesLister | None = None,
        playback_uri_resolver: PlaybackUriResolver | None = None,
        library_root: PurePosixPath | None = None,
        video_extensions: set[str] | None = None,
        subtitle_extensions: set[str] | None = None,
        subtitle_cache: SubtitleCache | None = None,
        napi_provider: SubtitleDownloadProvider | None = None,
        napi_saved_state: NapiSavedStateStore | None = None,
        video_reader: VideoRangeReader | None = None,
        file_repository: FileRepository | None = None,
        file_writer: FileWriter | None = None,
        napi_enabled: bool = False,
        napi_language: str = "ENG",
        sleep_inhibitor: SleepInhibitor | None = None,
        library_repository: LibraryRepository | None = None,
    ) -> None:
        super().__init__(parent)
        self.setVisible(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._focus_before_play: QWidget | None = None
        self._sleep_inhibitor = sleep_inhibitor
        self._video_area = VideoArea(
            on_close=self._request_close,
            files_lister=files_lister,
            playback_uri_resolver=playback_uri_resolver,
            library_root=library_root,
            video_extensions=video_extensions,
            subtitle_extensions=subtitle_extensions,
            subtitle_cache=subtitle_cache,
            napi_provider=napi_provider,
            napi_saved_state=napi_saved_state,
            video_reader=video_reader,
            file_repository=file_repository,
            file_writer=file_writer,
            napi_enabled=napi_enabled,
            napi_language=napi_language,
            library_repository=library_repository,
            parent=self,
        )

    def play(
        self,
        uri: str,
        library_path: PurePosixPath,
        *,
        resolved_video_path: PurePosixPath | None = None,
    ) -> None:
        self._focus_before_play = QApplication.focusWidget()
        parent = self.parentWidget()
        self.setGeometry(parent.rect() if parent is not None else self.rect())
        self._video_area.setGeometry(self.rect())
        self.show()
        self.raise_()
        self._video_area.mpv_widget.show()
        QApplication.processEvents()
        self._video_area.play_file(uri, library_path, resolved_video_path=resolved_video_path)
        if self._sleep_inhibitor is not None:
            self._sleep_inhibitor.acquire()
        self.grabKeyboard()
        self.activateWindow()
        self.setFocus()
        self._video_area.setFocus()

    def close_player(self) -> None:
        library_path = self._video_area.current_library_path
        saved_focus = self._focus_before_play
        self._focus_before_play = None
        self.releaseKeyboard()
        if self._sleep_inhibitor is not None:
            self._sleep_inhibitor.release()
        self._video_area.stop()
        self.hide()
        QTimer.singleShot(0, lambda: self._restore_focus(saved_focus, library_path))

    def _restore_focus(
        self,
        saved_focus: QWidget | None,
        library_path: PurePosixPath | None = None,
    ) -> None:
        parent = self.parentWidget()
        if (
            library_path is not None
            and parent is not None
            and hasattr(parent, "focus_playback_path")
            and parent.focus_playback_path(library_path)
        ):
            return
        if saved_focus is not None and isValid(saved_focus) and saved_focus.isVisible():
            saved_focus.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        if parent is not None and hasattr(parent, "restore_screen_focus"):
            parent.restore_screen_focus()

    def shutdown(self) -> None:
        if self._sleep_inhibitor is not None:
            self._sleep_inhibitor.release()
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
