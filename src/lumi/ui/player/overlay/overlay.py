"""Transparent overlay widget — wiring only."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QElapsedTimer, QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from lumi.ui.player.controller.controller import MpvController
from lumi.ui.player.controller.events import PlaybackState
from lumi.ui.player.controller.scrub_engine import ScrubEngine
from lumi.ui.player.controller.volume_engine import VolumeEngine
from lumi.ui.player.overlay.input_router import Command, InputRouter, RoutedCommand
from lumi.ui.player.overlay.layout.regions import compute_layout
from lumi.ui.player.overlay.paint.controls import paint_corner_hints, paint_cross_controls, paint_timeline
from lumi.ui.player.overlay.paint.tracks import paint_track_sheet
from lumi.ui.player.overlay.paint.volume import paint_volume
from lumi.ui.player.overlay.press_animation import PressAnimation, press_strength, release
from lumi.ui.player.overlay.state import (
    CROSS_ORDER,
    FocusZone,
    OverlayState,
    TrackKind,
    View,
    close_tracks,
    dismiss_controls,
    hide_controls,
    move_cross_focus,
    open_tracks,
    selected_track_index,
    show_controls,
    show_scrub,
    toggle_focus_zone,
)


class PlayerOverlay(QWidget):
    PRE_HIDE_FADE_MS = 1000
    FADED_OPACITY = 0.75
    HIDE_MS = 3500
    VOLUME_HIDE_MS = 2000
    PRESS_ANIM_MS = 16

    def __init__(
        self,
        controller: MpvController,
        *,
        on_close: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._controller = controller
        self._on_close = on_close
        self._router = InputRouter()
        self._state = OverlayState()
        self._layout = compute_layout(1280, 720, View.WATCHING, TrackKind.SUBTITLES, [])
        self._key_scrub_timer = QElapsedTimer()
        self._volume_adjust_timer = QElapsedTimer()
        self._volume_adjust_direction = 0
        self._volume_step_base = 1
        self._ui_opacity = 1.0
        self._hide_timer = QTimer(self)
        self._dim_timer = QTimer(self)
        self._volume_hide_timer = QTimer(self)
        self._seek_apply_timer = QTimer(self)
        self._key_scrub_tick_timer = QTimer(self)
        self._volume_adjust_tick_timer = QTimer(self)
        self._press_anim_timer = QTimer(self)
        self._press_anim: PressAnimation | None = None
        self._press_clock = QElapsedTimer()
        self._volume_baseline_set = False
        self._hide_timer.setSingleShot(True)
        self._dim_timer.setSingleShot(True)
        self._volume_hide_timer.setSingleShot(True)
        self._seek_apply_timer.setSingleShot(True)
        self._key_scrub_tick_timer.setInterval(33)
        self._volume_adjust_tick_timer.setInterval(33)
        self._press_anim_timer.setInterval(self.PRESS_ANIM_MS)
        self._press_anim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._hide_timer.timeout.connect(self._on_hide_timeout)
        self._dim_timer.timeout.connect(self._on_pre_hide_dim)
        self._volume_hide_timer.timeout.connect(self._on_volume_hide)
        self._seek_apply_timer.timeout.connect(self._apply_pending_seek)
        self._key_scrub_tick_timer.timeout.connect(self._on_key_scrub_tick)
        self._volume_adjust_tick_timer.timeout.connect(self._on_volume_adjust_tick)
        self._press_anim_timer.timeout.connect(self._on_press_anim_tick)
        self._controller.signals.state_changed.connect(self._on_playback_state)
        self._controller.signals.track_list_changed.connect(self._refresh_track_rows)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    @property
    def state(self) -> OverlayState:
        return self._state

    def bind(self):
        self._controller.bind()

    def unbind(self):
        self._hide_timer.stop()
        self._dim_timer.stop()
        self._volume_hide_timer.stop()
        self._seek_apply_timer.stop()
        self._key_scrub_tick_timer.stop()
        self._volume_adjust_tick_timer.stop()
        self._volume_adjust_direction = 0
        self._press_anim_timer.stop()
        self._press_anim = None
        self._controller.unbind()
        self.unsetCursor()
        if parent := self.parentWidget():
            parent.unsetCursor()

    def close_if_watching(self) -> bool:
        if self._state.view == View.WATCHING and self._on_close is not None:
            self._on_close()
            return True
        return False

    def _dismiss_to_watching(self) -> None:
        self._stop_key_scrub()
        self._state = dismiss_controls(self._state)
        self._hide_timer.stop()
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        self._sync_cursor()
        self._sync_overlay_visibility()
        self.update()

    def show_scrubber(self) -> None:
        self.show()
        self.raise_()
        self._state = show_scrub(self._state)
        self._sync_playback_to_scrub()
        self._hide_timer.stop()
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        self.setFocus()
        self._sync_cursor()
        self.update()

    def show_controls(self):
        self.show()
        self.raise_()
        self._state = show_controls(self._state)
        self._sync_playback_to_scrub()
        self._note_ui_activity()
        self.setFocus()
        self._sync_cursor()
        self.update()

    def start_watching(self) -> None:
        """Hide overlay so the OpenGL video layer is visible (required on macOS)."""
        self._state = hide_controls(self._state)
        self._hide_timer.stop()
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        self._sync_cursor()
        self._sync_overlay_visibility()

    def _sync_overlay_visibility(self) -> None:
        if self._state.view == View.WATCHING and not self._state.volume_flash:
            self.hide()
            parent = self.parentWidget()
            if parent is not None and hasattr(parent, "mpv_widget"):
                parent.mpv_widget.raise_()
        else:
            self.show()
            self.raise_()

    def set_media_info(self, _path: str):
        self._volume_baseline_set = False
        self._state.volume_flash = False
        self._volume_hide_timer.stop()
        self._stop_key_scrub(finalize=False)
        self._state.scrub = None
        self._state.time_pos = 0.0
        self._state.duration = 0.0
        self._controller.notify_media_loaded()
        self._sync_cursor()
        self.update()

    def _on_playback_state(self, playback: PlaybackState):
        prev_vol = self._state.volume
        prev_muted = self._state.muted
        self._state.volume = playback.volume
        self._state.muted = playback.muted
        self._state.paused = playback.paused
        scrub = self._state.ensure_scrub()
        if not scrub.is_scrubbing():
            self._state.time_pos = playback.time_pos
            scrub.time_pos = playback.time_pos
        self._state.duration = playback.duration
        scrub.duration = playback.duration
        if not self._volume_baseline_set:
            self._volume_baseline_set = True
        elif abs(playback.volume - prev_vol) > 0.5 or playback.muted != prev_muted:
            self._flash_volume()
            return
        if self._ui_anim_active():
            return
        if self._state.view in (View.WATCHING, View.SCRUB):
            if self._state.view == View.SCRUB:
                self.update()
            return
        self.update()

    def _sync_playback_to_scrub(self):
        time_pos = self._controller.time_pos()
        duration = self._controller.duration()
        scrub = self._state.ensure_scrub()
        self._state.time_pos = time_pos
        self._state.duration = duration
        self._state.paused = self._controller.is_paused()
        scrub.time_pos = time_pos
        scrub.duration = duration
        if duration > 0:
            scrub.scrub_fraction = time_pos / duration

    def _refresh_track_rows(self):
        if self._state.track_kind == TrackKind.SUBTITLES:
            self._state.track_rows = self._controller.subtitle_tracks()
        else:
            self._state.track_rows = self._controller.audio_tracks()
        if self._state.view == View.CONTROLS:
            self.update()

    def _rebuild_layout(self):
        rows = self._state.track_rows or []
        self._layout = compute_layout(
            self.width(), self.height(), self._state.view, self._state.track_kind, rows
        )
        self._state.panel_w = self._layout.panel_w

    def _sync_cursor(self):
        hide = self._controller.has_media() and self._state.view == View.WATCHING
        cursor = Qt.CursorShape.BlankCursor if hide else Qt.CursorShape.ArrowCursor
        self.setCursor(cursor)
        if parent := self.parentWidget():
            parent.setCursor(cursor)

    def _flash_volume(self):
        self._state.volume_flash = True
        self._volume_hide_timer.start(self.VOLUME_HIDE_MS)
        self._sync_overlay_visibility()
        self.update()

    def _on_volume_hide(self):
        self._state.volume_flash = False
        self._sync_overlay_visibility()
        self.update()

    def _is_key_scrubbing(self) -> bool:
        scrub = self._state.scrub
        return scrub is not None and scrub.keyboard_scrubbing

    def _is_ui_interaction_blocked(self) -> bool:
        if self._is_key_scrubbing():
            return True
        if self._volume_adjust_direction != 0:
            return True
        scrub = self._state.scrub
        return scrub is not None and scrub.seek_dragging

    def _on_pre_hide_dim(self) -> None:
        if self._is_ui_interaction_blocked():
            return
        if self._state.view not in (View.CONTROLS, View.SCRUB):
            return
        self._ui_opacity = self.FADED_OPACITY
        self.update()

    def _tracks_inactivity(self) -> bool:
        return self._state.view in (View.CONTROLS, View.SCRUB, View.TRACKS)

    def _note_ui_activity(self) -> None:
        if not self._tracks_inactivity():
            return
        if self._is_ui_interaction_blocked():
            return
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        if self._state.view in (View.CONTROLS, View.SCRUB):
            self._hide_timer.start(self.HIDE_MS)
            self._dim_timer.start(max(0, self.HIDE_MS - self.PRE_HIDE_FADE_MS))
        self.update()

    def _on_hide_timeout(self):
        if self._is_key_scrubbing():
            return
        if self._state.view == View.SCRUB:
            self._dismiss_to_watching()
            return
        self._state = hide_controls(self._state)
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        self._sync_cursor()
        self._sync_overlay_visibility()
        self.update()

    def _keyboard_activity(self):
        self._note_ui_activity()

    def _press_state(self) -> tuple[str | None, float]:
        anim = self._press_anim
        if anim is None:
            return None, 0.0
        return anim.key, press_strength(anim, self._press_clock.elapsed())

    def _begin_press(self, key: str) -> None:
        self._press_anim = PressAnimation(key=key, holding=True)
        self._press_clock.start()
        if not self._press_anim_timer.isActive():
            self._press_anim_timer.start()
        self.update()

    def _end_press(self) -> None:
        if self._press_anim is None or not self._press_anim.holding:
            return
        self._press_anim = release(self._press_anim, self._press_clock.elapsed())
        if not self._press_anim_timer.isActive():
            self._press_anim_timer.start()
        self.update()

    def _on_press_anim_tick(self) -> None:
        self._sync_press_anim_clock()
        if self._press_anim is not None:
            self.repaint()
        elif self._state.volume_flash:
            self.update()

    def _sync_press_anim_clock(self) -> None:
        if self._press_anim is None:
            self._press_anim_timer.stop()
            return
        _key, strength = self._press_state()
        if not self._press_anim.holding and strength <= 0.0:
            self._press_anim = None
            self._press_anim_timer.stop()

    def _ui_anim_active(self) -> bool:
        return self._press_anim is not None or self._state.volume_flash

    def notify_repaint_tick(self) -> None:
        """Optional extra repaint when mpv renders; timer drives press animation."""
        if self._press_anim is None:
            return
        self._sync_press_anim_clock()
        if self._press_anim is not None:
            self.repaint()

    def _press_key_for_command(self, cmd: RoutedCommand) -> str | None:
        if cmd.command == Command.HIT:
            if cmd.hit_key in ("subs", "audio"):
                return None
            return cmd.hit_key
        if cmd.command == Command.ACTIVATE_CROSS:
            return self._state.cross_focus
        if cmd.command == Command.TOGGLE_PAUSE:
            return "center"
        if cmd.command == Command.SELECT_TRACK:
            return f"track:{cmd.track_index}"
        if cmd.command == Command.OPEN_FILE:
            return "open"
        return None

    def _execute(self, cmd: RoutedCommand):
        c = cmd.command
        if c == Command.TOGGLE_PAUSE:
            self._controller.toggle_pause()
            if self._state.view == View.SCRUB:
                self._keyboard_activity()
                self.update()
            else:
                self.show_controls()
                self._keyboard_activity()
        elif c == Command.SHOW_CONTROLS:
            self.show_controls()
        elif c == Command.DISMISS_CONTROLS:
            self._dismiss_to_watching()
        elif c == Command.HIDE_UI:
            self._stop_key_scrub()
            if self._state.view == View.TRACKS:
                self._state = close_tracks(self._state)
                self.show_controls()
            elif self._state.view == View.WATCHING and self._on_close is not None:
                self._on_close()
            else:
                self._dismiss_to_watching()
        elif c == Command.OPEN_TRACKS and cmd.track_kind:
            self.show()
            self.raise_()
            self._state = open_tracks(self._state, cmd.track_kind)
            self._hide_timer.stop()
            self._dim_timer.stop()
            self._ui_opacity = 1.0
            self._refresh_track_rows()
            self._state.track_focus = selected_track_index(
                self._state, self._controller.current_sid(), self._controller.current_aid()
            )
            self._sync_cursor()
            self.update()
        elif c == Command.CLOSE_TRACKS:
            self._state = close_tracks(self._state)
            self.show_controls()
        elif c == Command.MOVE_CROSS_FOCUS:
            self._state = move_cross_focus(self._state, cmd.delta)
            self._keyboard_activity()
            self.update()
        elif c == Command.TOGGLE_FOCUS_ZONE:
            if self._state.focus_zone == FocusZone.TIMELINE:
                self._stop_key_scrub()
            self._state = toggle_focus_zone(self._state)
            self._keyboard_activity()
            self.update()
        elif c == Command.ACTIVATE_CROSS:
            self._handle_hit(self._state.cross_focus)
            self._keyboard_activity()
        elif c == Command.MOVE_TRACK_FOCUS:
            rows = self._state.track_rows or []
            self._state.track_focus = max(
                0, min(len(rows) - 1, self._state.track_focus + cmd.delta)
            )
            self._note_ui_activity()
            self.update()
        elif c == Command.SELECT_TRACK:
            self._select_track(cmd.track_index)
        elif c == Command.START_MOUSE_SCRUB:
            if self._state.view == View.WATCHING:
                self.show_scrubber()
            scrub = self._state.ensure_scrub()
            scrub.seek_dragging = True
            self.grabMouse()
            self._hide_timer.stop()
            self._dim_timer.stop()
            if cmd.pos:
                self._seek_at(cmd.pos, immediate=True)
        elif c == Command.MOUSE_SCRUB:
            pass
        elif c == Command.FINISH_MOUSE_SCRUB:
            scrub = self._state.ensure_scrub()
            scrub.seek_dragging = False
            self.releaseMouse()
            self._finish_scrub()
            if self._state.view == View.SCRUB:
                self._dismiss_to_watching()
            else:
                self.show_controls()
        elif c == Command.START_KEY_SCRUB:
            self._sync_playback_to_scrub()
            scrub = self._state.ensure_scrub()
            if scrub.duration <= 0:
                self._controller.seek_relative(cmd.delta * ScrubEngine.INITIAL_KEY_SCRUB_S)
                return
            if self._state.view == View.WATCHING:
                self.show_scrubber()
            self._hide_timer.stop()
            self._dim_timer.stop()
            self._ui_opacity = 1.0
            self._key_scrub_timer.start()
            scrub, seek, debounce = ScrubEngine.start_key_scrub(scrub, cmd.delta)
            self._controller.seek_relative(cmd.delta * ScrubEngine.INITIAL_KEY_SCRUB_S)
            self._apply_scrub_result(scrub, None, debounce)
            self._key_scrub_tick_timer.start()
            self._keyboard_activity()
        elif c == Command.STOP_KEY_SCRUB:
            self._stop_key_scrub()
            if self._state.view == View.SCRUB:
                self._dismiss_to_watching()
            self._keyboard_activity()
        elif c in (Command.TIMELINE_UP, Command.TIMELINE_DOWN):
            self._stop_key_scrub()
            if c == Command.TIMELINE_UP:
                self._state = self._state.__class__(
                    **{**self._state.__dict__, "focus_zone": FocusZone.CONTROLS}
                )
                self.update()
            elif c == Command.TIMELINE_DOWN:
                self._dismiss_to_watching()
            self._keyboard_activity()
        elif c == Command.HIT:
            if cmd.hit_key in CROSS_ORDER:
                self._state.cross_focus = cmd.hit_key
                self._state.focus_zone = FocusZone.CONTROLS
            self._handle_hit(cmd.hit_key)
        elif c == Command.CLICK_OUTSIDE:
            self._dismiss_to_watching()
        elif c == Command.START_VOLUME_ADJUST:
            self._start_volume_adjust(cmd.delta, cmd.volume_step)
        elif c == Command.STOP_VOLUME_ADJUST:
            self._stop_volume_adjust()
        elif c == Command.TOGGLE_MUTE:
            self._controller.toggle_mute()
            self._state.muted = self._controller.is_muted()
            self._flash_volume()
            if self._state.view != View.WATCHING:
                self._keyboard_activity()
            self.update()
        elif c == Command.KEYBOARD_ACTIVITY:
            self._keyboard_activity()

    def _handle_hit(self, key: str):
        if key == "m1":
            self._controller.seek_relative(-1)
        elif key == "m10":
            self._controller.seek_relative(-10)
        elif key == "center":
            self._controller.toggle_pause()
        elif key == "p10":
            self._controller.seek_relative(10)
        elif key == "p1":
            self._controller.seek_relative(1)
        elif key == "subs":
            self._execute(RoutedCommand(Command.OPEN_TRACKS, track_kind=TrackKind.SUBTITLES))
            return
        elif key == "audio":
            self._execute(RoutedCommand(Command.OPEN_TRACKS, track_kind=TrackKind.AUDIO))
            return
        elif key.startswith("track:"):
            self._select_track(int(key.split(":")[1]))
        self._sync_playback_to_scrub()
        self.show_controls()

    def _select_track(self, index: int):
        rows = self._state.track_rows or []
        if index < 0 or index >= len(rows):
            return
        track_id, _ = rows[index]
        if self._state.track_kind == TrackKind.SUBTITLES:
            self._controller.set_sid(track_id)
        else:
            self._controller.set_aid(track_id)
        self._refresh_track_rows()
        self.update()

    def _apply_scrub_result(self, scrub, seek, debounce):
        self._state.scrub = scrub
        self._state.time_pos = scrub.time_pos
        if scrub.duration > 0:
            self._state.duration = scrub.duration
        if seek:
            self._controller.seek_fraction(seek.fraction, exact=seek.exact)
        if debounce:
            self._seek_apply_timer.start(debounce)
        self.update()

    def _seek_at(self, pos: QPoint, *, immediate: bool = False):
        scrub = self._state.ensure_scrub()
        fraction = ScrubEngine.fraction_at(
            pos.x(), self._layout.seek_inner.x(), self._layout.seek_inner.width()
        )
        scrub, seek, debounce = ScrubEngine.scrub_to_fraction(scrub, fraction, immediate=immediate)
        self._apply_scrub_result(scrub, seek, debounce)

    def _finish_scrub(self):
        self._seek_apply_timer.stop()
        scrub = self._state.ensure_scrub()
        scrub, seek = ScrubEngine.finish_scrub(scrub, force=True)
        self._state.scrub = scrub
        self._state.time_pos = scrub.time_pos
        if seek:
            self._controller.seek_fraction(seek.fraction, exact=seek.exact)
        QTimer.singleShot(200, self._sync_playback_to_scrub)
        self.update()

    def _apply_pending_seek(self):
        scrub = self._state.ensure_scrub()
        scrub, seek = ScrubEngine.apply_pending(scrub)
        self._state.scrub = scrub
        if seek:
            scrub.key_scrub_dirty = True
            self._controller.seek_fraction(seek.fraction, exact=seek.exact)

    def _stop_key_scrub(self, *, finalize: bool = True):
        self._key_scrub_tick_timer.stop()
        scrub = self._state.ensure_scrub()
        held = self._key_scrub_timer.isValid() and self._key_scrub_timer.elapsed() > 80
        scrub, seek = ScrubEngine.stop_key_scrub(scrub, finalize=finalize and held)
        self._state.scrub = scrub
        if seek:
            self._controller.seek_fraction(seek.fraction, exact=seek.exact)
            self._state.time_pos = scrub.time_pos
        self.update()

    def _apply_volume_delta(self, delta: float) -> None:
        self._controller.change_volume(delta)
        self._state.volume = self._controller.volume()
        self._flash_volume()
        if self._state.view != View.WATCHING:
            self._keyboard_activity()
        self.update()

    def _start_volume_adjust(self, direction: int, step_base: int) -> None:
        self._volume_adjust_direction = direction
        self._volume_step_base = step_base
        self._volume_adjust_timer.start()
        self._apply_volume_delta(direction * step_base)
        self._volume_adjust_tick_timer.start()

    def _stop_volume_adjust(self) -> None:
        self._volume_adjust_tick_timer.stop()
        self._volume_adjust_direction = 0

    def _on_volume_adjust_tick(self) -> None:
        if self._volume_adjust_direction == 0:
            return
        step = VolumeEngine.step(
            self._volume_adjust_timer.elapsed(),
            step_base=self._volume_step_base,
        )
        self._apply_volume_delta(self._volume_adjust_direction * step)

    def _on_key_scrub_tick(self):
        scrub = self._state.ensure_scrub()
        scrub.key_scrub_elapsed_ms = self._key_scrub_timer.elapsed()
        scrub, seek, debounce = ScrubEngine.key_scrub_tick(scrub)
        self._apply_scrub_result(scrub, seek, debounce)

    def keyPressEvent(self, event):
        if routed := self._router.route_key(
            event, self._state, has_media=self._controller.has_media()
        ):
            if not event.isAutoRepeat():
                if key := self._press_key_for_command(routed):
                    self._begin_press(key)
            self._execute(routed)
            if routed.command != Command.SHOW_CONTROLS or self._state.view != View.WATCHING:
                event.accept()
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        self._end_press()
        if routed := self._router.route_key_release(event, self._state):
            self._execute(routed)
            event.accept()
            return
        super().keyReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        scrub = self._state.scrub
        if scrub and scrub.seek_dragging:
            self._seek_at(event.position().toPoint())
            return
        if self._tracks_inactivity():
            self._note_ui_activity()
        if routed := self._router.route_mouse_move(self._state, scrubbing=False):
            if routed.command == Command.SHOW_CONTROLS:
                self.show_controls()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._end_press()
        scrub = self._state.scrub
        if routed := self._router.route_mouse_release(
            event, scrubbing=bool(scrub and scrub.seek_dragging)
        ):
            self._execute(routed)
            return
        self.update()
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if self._state.view in (View.CONTROLS, View.TRACKS, View.SCRUB):
            self._rebuild_layout()
        routed = self._router.route_mouse_press(
            event,
            self._state,
            self._layout.hit_regions,
            has_media=self._controller.has_media(),
            in_controls_area=lambda pos: any(
                r.contains(pos) for r in self._layout.hit_regions.values()
            ),
        )
        if routed:
            if key := self._press_key_for_command(routed):
                self._begin_press(key)
            self._execute(routed)
            return
        super().mousePressEvent(event)

    def paintEvent(self, _event: QPaintEvent):
        w, h = self.width(), self.height()
        if not self._controller.has_media():
            self._after_paint_anim()
            return

        if self._state.view == View.WATCHING:
            if self._state.volume_flash:
                painter = QPainter(self)
                if painter.isActive():
                    try:
                        painter.save()
                        painter.setOpacity(self._ui_opacity)
                        paint_volume(painter, w, h, self._state.volume, muted=self._state.muted)
                        painter.restore()
                    finally:
                        painter.end()
            self._after_paint_anim()
            return

        self._rebuild_layout()
        press_key, press_strength_val = self._press_state()
        painter = QPainter(self)
        if not painter.isActive():
            return
        try:
            painter.save()
            painter.setOpacity(self._ui_opacity)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            if self._state.view == View.CONTROLS:
                paint_cross_controls(
                    painter,
                    self._state,
                    self._layout,
                    playing=self._controller.is_playing(),
                    press_key=press_key,
                    press_strength=press_strength_val,
                )
                paint_corner_hints(
                    painter,
                    self._layout,
                    subtitle_name=self._controller.current_subtitle_label(),
                    audio_name=self._controller.current_audio_label(),
                )
                if self._state.volume_flash:
                    paint_volume(painter, w, h, self._state.volume, muted=self._state.muted)
            elif self._state.view == View.SCRUB:
                paint_timeline(
                    painter,
                    self._state,
                    self._layout,
                    timeline_focused=True,
                )
            elif self._state.view == View.TRACKS:
                painter.fillRect(self.rect(), QColor.fromRgbF(0, 0, 0, 0.42))
                paint_track_sheet(
                    painter,
                    w,
                    h,
                    self._state,
                    self._layout,
                    sid=self._controller.current_sid(),
                    aid=self._controller.current_aid(),
                    press_key=press_key,
                    press_strength=press_strength_val,
                )
        finally:
            painter.restore()
            painter.end()

        self._after_paint_anim()

    def _after_paint_anim(self) -> None:
        self._sync_press_anim_clock()
        if self._press_anim is not None and not self._press_anim_timer.isActive():
            self._press_anim_timer.start()
