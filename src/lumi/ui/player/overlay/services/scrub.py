from __future__ import annotations

from PySide6.QtCore import QPoint, QTimer

from lumi.ui.player.controller.scrub_engine import ScrubEngine
from lumi.ui.player.overlay.services.base import OverlayService


class ScrubService(OverlayService):
    def is_key_scrubbing(self) -> bool:
        scrub = self._rt.state.scrub
        return scrub is not None and scrub.keyboard_scrubbing

    def apply_result(self, scrub, seek, debounce):
        self._rt.state.scrub = scrub
        self._rt.state.time_pos = scrub.time_pos
        if scrub.duration > 0:
            self._rt.state.duration = scrub.duration
        if seek:
            self._rt.controller.seek_fraction(seek.fraction, exact=seek.exact)
        if debounce:
            self._rt.seek_apply_timer.start(debounce)
        self._update()

    def seek_at(self, pos: QPoint, *, immediate: bool = False):
        scrub = self._rt.state.ensure_scrub()
        fraction = ScrubEngine.fraction_at(
            pos.x(), self._rt.layout.seek_inner.x(), self._rt.layout.seek_inner.width()
        )
        scrub, seek, debounce = ScrubEngine.scrub_to_fraction(scrub, fraction, immediate=immediate)
        self._o.scrub.apply_result(scrub, seek, debounce)

    def finish(self):
        self._rt.seek_apply_timer.stop()
        scrub = self._rt.state.ensure_scrub()
        scrub, seek = ScrubEngine.finish_scrub(scrub, force=True)
        self._rt.state.scrub = scrub
        self._rt.state.time_pos = scrub.time_pos
        if seek:
            self._rt.controller.seek_fraction(seek.fraction, exact=seek.exact)
        QTimer.singleShot(200, self._sync_playback_to_scrub)
        self._update()

    def apply_pending_seek(self):
        scrub = self._rt.state.ensure_scrub()
        scrub, seek = ScrubEngine.apply_pending(scrub)
        self._rt.state.scrub = scrub
        if seek:
            scrub.key_scrub_dirty = True
            self._rt.controller.seek_fraction(seek.fraction, exact=seek.exact)

    def stop_key_scrub(self, *, finalize: bool = True):
        self._rt.key_scrub_tick_timer.stop()
        scrub = self._rt.state.ensure_scrub()
        held = self._rt.key_scrub_timer.isValid() and self._rt.key_scrub_timer.elapsed() > 80
        scrub, seek = ScrubEngine.stop_key_scrub(scrub, finalize=finalize and held)
        self._rt.state.scrub = scrub
        if seek:
            self._rt.controller.seek_fraction(seek.fraction, exact=seek.exact)
            self._rt.state.time_pos = scrub.time_pos
        self._update()

    def on_key_scrub_tick(self):
        scrub = self._rt.state.ensure_scrub()
        scrub.key_scrub_elapsed_ms = self._rt.key_scrub_timer.elapsed()
        scrub, seek, debounce = ScrubEngine.key_scrub_tick(scrub)
        self._o.scrub.apply_result(scrub, seek, debounce)
