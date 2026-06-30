from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import View
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, _cmd: RoutedCommand) -> None:
    overlay._rt.controller.toggle_mute()
    overlay._rt.state.muted = overlay._rt.controller.is_muted()
    overlay.volume.flash()
    if overlay._rt.state.view != View.WATCHING:
        overlay.activity.keyboard_activity()
    overlay.update()


register(Command.TOGGLE_MUTE, handle)
