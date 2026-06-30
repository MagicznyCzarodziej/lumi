from __future__ import annotations

from lumi.ui.player.controller.scrub_engine import ScrubEngine
from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import View
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, cmd: RoutedCommand) -> None:
    overlay.playback.sync_to_scrub()
    scrub = overlay._rt.state.ensure_scrub()
    if scrub.duration <= 0:
        overlay._rt.controller.seek_relative(cmd.delta * ScrubEngine.INITIAL_KEY_SCRUB_S)
        return
    if overlay._rt.state.view == View.WATCHING:
        overlay.activity.show_scrubber()
    overlay._rt.hide_timer.stop()
    overlay._rt.dim_timer.stop()
    overlay._rt.ui_opacity = 1.0
    overlay._rt.key_scrub_timer.start()
    scrub, seek, debounce = ScrubEngine.start_key_scrub(scrub, cmd.delta)
    overlay._rt.controller.seek_relative(cmd.delta * ScrubEngine.INITIAL_KEY_SCRUB_S)
    overlay.scrub.apply_result(scrub, None, debounce)
    overlay._rt.key_scrub_tick_timer.start()
    overlay.activity.keyboard_activity()


register(Command.START_KEY_SCRUB, handle)
