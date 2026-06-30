from __future__ import annotations

from lumi.ui.player.controller.scrub_engine import ScrubEngine
from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import View
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, cmd: RoutedCommand) -> None:
    overlay.scrub.stop_key_scrub()
    scrub = overlay._rt.state.ensure_scrub()
    scrub, seek, debounce = ScrubEngine.scrub_to_fraction(
        scrub, cmd.fraction, immediate=True
    )
    overlay.scrub.apply_result(scrub, seek, debounce)
    if overlay._rt.state.view != View.WATCHING:
        overlay.activity.keyboard_activity()


register(Command.SEEK_TO_FRACTION, handle)
