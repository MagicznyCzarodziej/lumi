from __future__ import annotations

from PySide6.QtCore import Qt

from lumi.ui.player.overlay.press_animation import PressAnimation, press_strength, release
from lumi.ui.player.overlay.services.base import OverlayService
from lumi.ui.player.overlay.state import View, dismiss_controls, hide_controls, show_controls, show_scrub


class ActivityService(OverlayService):
    def dismiss_to_watching(self) -> None:
        self._o.scrub.stop_key_scrub()
        self._rt.state = dismiss_controls(self._rt.state)
        self._rt.hide_timer.stop()
        self._rt.dim_timer.stop()
        self._rt.ui_opacity = 1.0
        self._o.activity.sync_cursor()
        self._o.activity.sync_overlay_visibility()
        self._update()

    def show_scrubber(self) -> None:
        self._o.show()
        self._o.raise_()
        self._rt.state = show_scrub(self._rt.state)
        self._o.playback.sync_to_scrub()
        self._rt.hide_timer.stop()
        self._rt.dim_timer.stop()
        self._rt.ui_opacity = 1.0
        self._o.setFocus()
        self._o.activity.sync_cursor()
        self._update()

    def show_controls(self):
        self._o.show()
        self._o.raise_()
        self._rt.state = show_controls(self._rt.state)
        self._o.playback.sync_to_scrub()
        self._o.activity.note_ui_activity()
        self._o.setFocus()
        self._o.activity.sync_cursor()
        self._update()

    def start_watching(self) -> None:
        """Hide overlay so the OpenGL video layer is visible (required on macOS)."""
        self._rt.state = hide_controls(self._rt.state)
        self._rt.hide_timer.stop()
        self._rt.dim_timer.stop()
        self._rt.ui_opacity = 1.0
        self._o.activity.sync_cursor()
        self._o.activity.sync_overlay_visibility()

    def sync_overlay_visibility(self) -> None:
        if self._rt.state.view == View.WATCHING and not self._rt.state.volume_flash:
            self._o.hide()
            parent = self._o.parentWidget()
            if parent is not None and hasattr(parent, "mpv_widget"):
                parent.mpv_widget.raise_()
        else:
            self._o.show()
            self._o.raise_()

    def scroll_panel_by(self, delta_y: int) -> None:
        if self._rt.state.view not in (View.TRACKS, View.VIDEO, View.SUBTITLE_BROWSE):
            return
        self._o.panel.rebuild()
        step = max(24, self._rt.layout.metrics.track_row_h)
        notches = delta_y // 120 if delta_y else 0
        if notches == 0:
            notches = 1 if delta_y > 0 else -1
        self._rt.state.panel_scroll_y = max(
            0,
            min(
                self._rt.layout.panel_scroll_max,
                self._rt.state.panel_scroll_y - notches * step,
            ),
        )
        self._o.panel.rebuild()
        self._o.activity.note_ui_activity()
        self._update()

    def sync_cursor(self):
        hide = self._rt.controller.has_media() and self._rt.state.view == View.WATCHING
        cursor = Qt.CursorShape.BlankCursor if hide else Qt.CursorShape.ArrowCursor
        self._o.setCursor(cursor)
        if parent := self._o.parentWidget():
            parent.setCursor(cursor)

    def is_ui_interaction_blocked(self) -> bool:
        if self._o.scrub.is_key_scrubbing():
            return True
        if self._rt.volume_adjust_direction != 0:
            return True
        scrub = self._rt.state.scrub
        return scrub is not None and scrub.seek_dragging

    def on_pre_hide_dim(self) -> None:
        if self._o.activity.is_ui_interaction_blocked():
            return
        if self._rt.state.view not in (View.CONTROLS, View.SCRUB):
            return
        self._rt.ui_opacity = self._o.FADED_OPACITY
        self._update()

    def tracks_inactivity(self) -> bool:
        return self._rt.state.view in (
            View.CONTROLS,
            View.SCRUB,
            View.TRACKS,
            View.VIDEO,
            View.SUBTITLE_BROWSE,
        )

    def note_ui_activity(self) -> None:
        if not self._o.activity.tracks_inactivity():
            return
        if self._o.activity.is_ui_interaction_blocked():
            return
        self._rt.dim_timer.stop()
        self._rt.ui_opacity = 1.0
        if self._rt.state.view == View.SCRUB:
            hide_ms = self._o.SCRUB_HIDE_MS
            self._rt.hide_timer.start(hide_ms)
            self._rt.dim_timer.start(max(0, hide_ms - self._o.PRE_HIDE_FADE_MS))
        elif self._rt.state.view == View.CONTROLS:
            self._rt.hide_timer.start(self._o.HIDE_MS)
            self._rt.dim_timer.start(max(0, self._o.HIDE_MS - self._o.PRE_HIDE_FADE_MS))
        self._update()

    def on_hide_timeout(self):
        if self._o.scrub.is_key_scrubbing():
            return
        if self._rt.state.view == View.SCRUB:
            self._o.activity.dismiss_to_watching()
            return
        self._rt.state = hide_controls(self._rt.state)
        self._rt.dim_timer.stop()
        self._rt.ui_opacity = 1.0
        self._o.activity.sync_cursor()
        self._o.activity.sync_overlay_visibility()
        self._update()

    def keyboard_activity(self):
        self._o.activity.note_ui_activity()

    def press_state(self) -> tuple[str | None, float]:
        anim = self._rt.press_anim
        if anim is None:
            return None, 0.0
        return anim.key, press_strength(anim, self._rt.press_clock.elapsed())

    def begin_press(self, key: str) -> None:
        self._rt.press_anim = PressAnimation(key=key, holding=True)
        self._rt.press_clock.start()
        if not self._rt.press_anim_timer.isActive():
            self._rt.press_anim_timer.start()
        self._update()

    def end_press(self) -> None:
        if self._rt.press_anim is None or not self._rt.press_anim.holding:
            return
        self._rt.press_anim = release(self._rt.press_anim, self._rt.press_clock.elapsed())
        if not self._rt.press_anim_timer.isActive():
            self._rt.press_anim_timer.start()
        self._update()

    def on_press_anim_tick(self) -> None:
        self._o.activity.sync_press_anim_clock()
        if self._rt.press_anim is not None:
            self._o.repaint()
        elif self._rt.state.volume_flash:
            self._update()

    def sync_press_anim_clock(self) -> None:
        if self._rt.press_anim is None:
            self._rt.press_anim_timer.stop()
            return
        _key, strength = self._o.activity.press_state()
        if not self._rt.press_anim.holding and strength <= 0.0:
            self._rt.press_anim = None
            self._rt.press_anim_timer.stop()

    def ui_anim_active(self) -> bool:
        return self._rt.press_anim is not None or self._rt.state.volume_flash

    def after_paint_anim(self) -> None:
        self.sync_press_anim_clock()
        if self._rt.press_anim is not None and not self._rt.press_anim_timer.isActive():
            self._rt.press_anim_timer.start()

    def notify_repaint_tick(self) -> None:
        """Optional extra repaint when mpv renders; timer drives press animation."""
        if self._rt.press_anim is None:
            return
        self.sync_press_anim_clock()
        if self._rt.press_anim is not None:
            self._o.repaint()
