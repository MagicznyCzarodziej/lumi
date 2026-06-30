"""Mutable overlay session state — no Qt behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from PySide6.QtCore import QElapsedTimer, QThreadPool, QTimer

from lumi.ui.player.controller.controller import MpvController
from lumi.ui.player.overlay.deps import OverlayDeps
from lumi.ui.player.overlay.input_router import InputRouter
from lumi.ui.player.overlay.layout.regions import LayoutSnapshot, compute_layout
from lumi.ui.player.overlay.press_animation import PressAnimation
from lumi.ui.player.overlay.state import OverlayState, TrackKind, View

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


@dataclass
class OverlayRuntime:
    controller: MpvController
    deps: OverlayDeps
    hide_timer: QTimer
    dim_timer: QTimer
    volume_hide_timer: QTimer
    seek_apply_timer: QTimer
    key_scrub_tick_timer: QTimer
    volume_adjust_tick_timer: QTimer
    press_anim_timer: QTimer
    state: OverlayState = field(default_factory=OverlayState)
    layout: LayoutSnapshot = field(
        default_factory=lambda: compute_layout(1280, 720, View.WATCHING, TrackKind.SUBTITLES, [])
    )
    router: InputRouter = field(default_factory=InputRouter)
    thread_pool: QThreadPool = field(default_factory=QThreadPool.globalInstance)

    library_path: PurePosixPath | None = None
    resolved_video_path: PurePosixPath | None = None
    stream_uri: str | None = None
    selected_subtitle_path: PurePosixPath | None = None
    pending_track_restore: bool = False
    pending_aspect_restore: bool = False
    restoring_track_selection: bool = False
    browse_target: PurePosixPath | None = None
    browse_busy: bool = False
    napi_downloading: bool = False
    napi_saving: bool = False
    napi_status_message: str | None = None
    volume_baseline_set: bool = False
    ui_opacity: float = 1.0
    volume_adjust_direction: int = 0
    volume_step_base: int = 1
    press_anim: PressAnimation | None = None

    key_scrub_timer: QElapsedTimer = field(default_factory=QElapsedTimer)
    volume_adjust_timer: QElapsedTimer = field(default_factory=QElapsedTimer)
    press_clock: QElapsedTimer = field(default_factory=QElapsedTimer)

    @classmethod
    def for_widget(cls, widget: QWidget, controller: MpvController, deps: OverlayDeps) -> OverlayRuntime:
        return cls(
            controller=controller,
            deps=deps,
            hide_timer=QTimer(widget),
            dim_timer=QTimer(widget),
            volume_hide_timer=QTimer(widget),
            seek_apply_timer=QTimer(widget),
            key_scrub_tick_timer=QTimer(widget),
            volume_adjust_tick_timer=QTimer(widget),
            press_anim_timer=QTimer(widget),
        )
