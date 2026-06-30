from __future__ import annotations

from lumi.ui.player.controller.volume_engine import VolumeEngine
from lumi.ui.player.overlay.services.base import OverlayService
from lumi.ui.player.overlay.state import View


class VolumeService(OverlayService):
    def flash(self):
        self._rt.state.volume_flash = True
        self._rt.volume_hide_timer.start(self._o.VOLUME_HIDE_MS)
        self._o.activity.sync_overlay_visibility()
        self._update()

    def on_hide(self):
        self._rt.state.volume_flash = False
        self._o.activity.sync_overlay_visibility()
        self._update()

    def apply_delta(self, delta: float) -> None:
        self._rt.controller.change_volume(delta)
        self._rt.state.volume = self._rt.controller.volume()
        self.flash()
        if self._rt.state.view != View.WATCHING:
            self._o.activity.keyboard_activity()
        self._update()

    def start_adjust(self, direction: int, step_base: int) -> None:
        self._rt.volume_adjust_direction = direction
        self._rt.volume_step_base = step_base
        self._rt.volume_adjust_timer.start()
        self.apply_delta(direction * step_base)
        self._rt.volume_adjust_tick_timer.start()

    def stop_adjust(self) -> None:
        self._rt.volume_adjust_tick_timer.stop()
        self._rt.volume_adjust_direction = 0

    def on_adjust_tick(self) -> None:
        if self._rt.volume_adjust_direction == 0:
            return
        step = VolumeEngine.step(
            self._rt.volume_adjust_timer.elapsed(),
            step_base=self._rt.volume_step_base,
        )
        self.apply_delta(self._rt.volume_adjust_direction * step)
