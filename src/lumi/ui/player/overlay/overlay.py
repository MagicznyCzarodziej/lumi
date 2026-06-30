"""Transparent overlay widget — wiring only."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtWidgets import QWidget

from lumi.ui.player.controller.controller import MpvController
from lumi.ui.player.overlay.commands import handle_hit, press_key_for_command, process_command
from lumi.ui.player.overlay.deps import OverlayDeps
from lumi.ui.player.overlay.events import OverlayEvents
from lumi.ui.player.overlay.input_router import RoutedCommand
from lumi.ui.player.overlay.services import (
    ActivityService,
    BrowseService,
    LayoutService,
    NapiService,
    PlaybackService,
    ScrubService,
    SubtitleService,
    TrackService,
    VolumeService,
)
from lumi.ui.player.overlay.setup import (
    build_runtime,
    configure_widget,
    connect_controller,
    install_timers,
)
from lumi.ui.player.overlay.state import OverlayState, View
from lumi.ui.player.overlay.worker_slots import OverlayWorkerSlots


class PlayerOverlay(QWidget):
    PRE_HIDE_FADE_MS = 1000
    FADED_OPACITY = 0.75
    HIDE_MS = 3500
    VOLUME_HIDE_MS = 2000
    PRESS_ANIM_MS = 16

    def __init__(
        self,
        controller: MpvController,
        deps: OverlayDeps | None = None,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        resolved = deps or OverlayDeps()
        self._rt = build_runtime(self, controller, resolved)
        self._events = OverlayEvents(self)
        self.activity = ActivityService(self)
        self.panel = LayoutService(self)
        self.playback = PlaybackService(self)
        self.scrub = ScrubService(self)
        self.volume = VolumeService(self)
        self.tracks = TrackService(self)
        self.browse = BrowseService(self)
        self.subtitles = SubtitleService(self)
        self.napi = NapiService(self)
        self._worker_slots = OverlayWorkerSlots(self)
        install_timers(self)
        connect_controller(self, controller)
        configure_widget(self)

    @property
    def state(self) -> OverlayState:
        return self._rt.state

    @property
    def controller(self) -> MpvController:
        return self._rt.controller

    def bind(self) -> None:
        self._rt.controller.bind()

    def unbind(self) -> None:
        rt = self._rt
        rt.hide_timer.stop()
        rt.dim_timer.stop()
        rt.volume_hide_timer.stop()
        rt.seek_apply_timer.stop()
        rt.key_scrub_tick_timer.stop()
        rt.volume_adjust_tick_timer.stop()
        rt.volume_adjust_direction = 0
        rt.press_anim_timer.stop()
        rt.press_anim = None
        rt.controller.unbind()
        self.unsetCursor()
        if parent := self.parentWidget():
            parent.unsetCursor()

    def close_if_watching(self) -> bool:
        if self._rt.state.view == View.WATCHING and self._rt.deps.on_close is not None:
            self._rt.deps.on_close()
            return True
        return False

    def execute_command(self, cmd: RoutedCommand) -> None:
        process_command(self, cmd)

    def press_key_for_command(self, cmd: RoutedCommand) -> str | None:
        return press_key_for_command(self, cmd)

    def handle_hit(self, key: str) -> None:
        handle_hit(self, key)

    def keyPressEvent(self, event) -> None:
        self._events.keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        self._events.keyReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        self._events.wheelEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self._events.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._events.mouseReleaseEvent(event)

    def mousePressEvent(self, event) -> None:
        self._events.mousePressEvent(event)

    def paintEvent(self, event) -> None:
        self._events.paintEvent(event)

    def notify_repaint_tick(self) -> None:
        self.activity.notify_repaint_tick()

    def set_media_info(
        self,
        stream_uri: str,
        library_path: PurePosixPath | None = None,
        *,
        resolved_video_path: PurePosixPath | None = None,
    ) -> None:
        self.playback.set_media_info(
            stream_uri,
            library_path,
            resolved_video_path=resolved_video_path,
        )

    def persist_track_selection(self) -> None:
        self.tracks.persist_track_selection()

    def persist_video_aspect(self) -> None:
        self.playback.persist_video_aspect()

    def show_controls(self) -> None:
        self.activity.show_controls()

    def start_watching(self) -> None:
        self.activity.start_watching()
