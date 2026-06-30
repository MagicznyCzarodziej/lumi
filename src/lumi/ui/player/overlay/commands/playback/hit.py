from __future__ import annotations

from lumi.ui.player.overlay.commands.handle_hit import handle_hit
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.state import FocusZone, cross_order
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, cmd: RoutedCommand) -> None:
    order = cross_order(
        prev_ep=overlay._rt.state.prev_ep_available,
        next_ep=overlay._rt.state.next_ep_available,
    )
    if cmd.hit_key in order:
        overlay._rt.state.cross_focus = cmd.hit_key
        overlay._rt.state.focus_zone = FocusZone.CONTROLS
    handle_hit(overlay, cmd.hit_key)


register(Command.HIT, handle)
