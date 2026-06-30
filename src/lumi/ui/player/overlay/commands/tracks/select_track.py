from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, cmd: RoutedCommand) -> None:
    overlay.tracks.select(cmd.track_index)


register(Command.SELECT_TRACK, handle)
