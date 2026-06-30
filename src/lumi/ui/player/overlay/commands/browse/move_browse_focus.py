from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register, refresh_panel
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, cmd: RoutedCommand) -> None:
    browse_rows = overlay._rt.state.browse_rows or []
    overlay._rt.state.browse_focus = max(
        0, min(len(browse_rows) - 1, overlay._rt.state.browse_focus + cmd.delta)
    )
    refresh_panel(overlay)


register(Command.MOVE_BROWSE_FOCUS, handle)
