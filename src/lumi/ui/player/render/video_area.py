"""Video compositor: mpv widget + overlay."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import PurePosixPath

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QWidget

from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.file_writer import FileWriter
from lumi.domain.filesystem.files_lister import FilesLister
from lumi.domain.filesystem.video_range_reader import VideoRangeReader
from lumi.domain.playback import PlaybackUriResolver
from lumi.domain.subtitles.cache import SubtitleCache
from lumi.domain.subtitles.provider import SubtitleDownloadProvider
from lumi.domain.subtitles.saved_state import NapiSavedStateStore
from lumi.infrastructure.watch_progress import load_watch_position, save_watch_position
from lumi.ui.player.controller.controller import MpvController
from lumi.ui.player.overlay.deps import OverlayDeps
from lumi.ui.player.overlay.input_router import is_dismiss_key
from lumi.ui.player.overlay.overlay import PlayerOverlay
from lumi.ui.player.render.mpv_widget import MpvWidget


class VideoArea(QWidget):
    def __init__(
        self,
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
        self.overlay = PlayerOverlay(
            self.controller,
            OverlayDeps(
                files_lister=files_lister,
                playback_uri_resolver=playback_uri_resolver,
                library_root=library_root,
                video_extensions=frozenset(video_extensions or ()),
                subtitle_extensions=frozenset(subtitle_extensions or ()),
                subtitle_cache=subtitle_cache,
                napi_provider=napi_provider,
                napi_saved_state=napi_saved_state,
                video_reader=video_reader,
                file_repository=file_repository,
                file_writer=file_writer,
                napi_enabled=napi_enabled,
                napi_language=napi_language,
                on_close=on_close,
            ),
            parent=self,
        )
        self.overlay.raise_()
        self.overlay.bind()
        self.mpv_widget.render_update.connect(
            self.overlay.notify_repaint_tick,
            Qt.ConnectionType.QueuedConnection,
        )
        self._library_path: PurePosixPath | None = None

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        rect = self.rect()
        self.mpv_widget.setGeometry(rect)
        self.overlay.setGeometry(rect)
        if self.overlay.isVisible():
            self.overlay.raise_()

    def play_file(
        self,
        path: str,
        library_path: PurePosixPath,
        *,
        resolved_video_path: PurePosixPath | None = None,
    ) -> None:
        if self._library_path is not None:
            self._persist_playback_state()
        self._library_path = library_path
        start_at = load_watch_position(library_path)
        self.mpv_widget.show()
        self.mpv_widget.raise_()
        self.overlay.set_media_info(
            path,
            library_path,
            resolved_video_path=resolved_video_path,
        )
        self.mpv_widget.play_file(path, start_at=start_at)
        self.overlay.start_watching()
        QApplication.processEvents()
        self.setFocus()

    def stop(self) -> None:
        self._persist_playback_state()
        self._library_path = None
        self.mpv_widget.stop()

    def shutdown(self) -> None:
        self._persist_playback_state()
        self._library_path = None
        self.overlay.unbind()
        self.mpv_widget.shutdown()

    def _persist_playback_state(self) -> None:
        self._persist_watch_progress()
        self.overlay.persist_track_selection()
        self.overlay.persist_video_aspect()

    def _persist_watch_progress(self) -> None:
        library_path = self._library_path
        if library_path is None:
            return
        duration = self.controller.duration()
        save_watch_position(
            library_path,
            self.controller.time_pos(),
            duration=duration if duration > 0 else None,
        )

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
