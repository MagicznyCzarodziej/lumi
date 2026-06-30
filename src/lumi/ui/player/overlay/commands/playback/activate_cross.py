from __future__ import annotations

from lumi.ui.player.overlay.commands.handle_hit import handle_hit
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.commands.processor import register
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, _cmd: RoutedCommand) -> None:
    handle_hit(overlay, overlay._rt.state.cross_focus)
    overlay.activity.keyboard_activity()


register(Command.ACTIVATE_CROSS, handle)
