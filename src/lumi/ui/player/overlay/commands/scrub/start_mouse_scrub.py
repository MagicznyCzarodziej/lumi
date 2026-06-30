from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import View
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, cmd: RoutedCommand) -> None:
    if overlay._rt.state.view == View.WATCHING:
        overlay.activity.show_scrubber()
    scrub = overlay._rt.state.ensure_scrub()
    scrub.seek_dragging = True
    overlay.grabMouse()
    overlay._rt.hide_timer.stop()
    overlay._rt.dim_timer.stop()
    if cmd.pos:
        overlay.scrub.seek_at(cmd.pos, immediate=True)


register(Command.START_MOUSE_SCRUB, handle)
