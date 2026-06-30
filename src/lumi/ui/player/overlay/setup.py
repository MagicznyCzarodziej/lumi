"""Overlay widget initialization helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QElapsedTimer, Qt, QTimer
from PySide6.QtWidgets import QSizePolicy

from lumi.ui.player.controller.controller import MpvController
from lumi.ui.player.overlay.deps import OverlayDeps
from lumi.ui.player.overlay.runtime import OverlayRuntime

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay


def build_runtime(widget: PlayerOverlay, controller: MpvController, deps: OverlayDeps) -> OverlayRuntime:
    return OverlayRuntime.for_widget(widget, controller, deps)


def install_timers(overlay: PlayerOverlay) -> None:
    rt = overlay._rt
    rt.key_scrub_timer = QElapsedTimer()
    rt.volume_adjust_timer = QElapsedTimer()
    rt.press_clock = QElapsedTimer()

    rt.hide_timer.setSingleShot(True)
    rt.dim_timer.setSingleShot(True)
    rt.volume_hide_timer.setSingleShot(True)
    rt.seek_apply_timer.setSingleShot(True)
    rt.key_scrub_tick_timer.setInterval(33)
    rt.volume_adjust_tick_timer.setInterval(33)
    rt.press_anim_timer.setInterval(overlay.PRESS_ANIM_MS)
    rt.press_anim_timer.setTimerType(Qt.TimerType.PreciseTimer)

    rt.hide_timer.timeout.connect(overlay.activity.on_hide_timeout)
    rt.dim_timer.timeout.connect(overlay.activity.on_pre_hide_dim)
    rt.volume_hide_timer.timeout.connect(overlay.volume.on_hide)
    rt.seek_apply_timer.timeout.connect(overlay.scrub.apply_pending_seek)
    rt.key_scrub_tick_timer.timeout.connect(overlay.scrub.on_key_scrub_tick)
    rt.volume_adjust_tick_timer.timeout.connect(overlay.volume.on_adjust_tick)
    rt.press_anim_timer.timeout.connect(overlay.activity.on_press_anim_tick)


def connect_controller(overlay: PlayerOverlay, controller: MpvController) -> None:
    controller.signals.state_changed.connect(overlay.playback.on_playback_state)
    controller.signals.track_list_changed.connect(overlay.tracks.on_track_list_changed)


def configure_widget(overlay: PlayerOverlay) -> None:
    overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    overlay.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
    overlay.setAutoFillBackground(False)
    overlay.setMouseTracking(True)
    overlay.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    overlay.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
