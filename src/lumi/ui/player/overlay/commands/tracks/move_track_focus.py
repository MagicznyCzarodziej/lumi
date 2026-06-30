from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register, refresh_panel
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import move_track_focus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, cmd: RoutedCommand) -> None:
    overlay._rt.state = move_track_focus(overlay._rt.state, cmd.delta)
    refresh_panel(overlay)


register(Command.MOVE_TRACK_FOCUS, handle)
