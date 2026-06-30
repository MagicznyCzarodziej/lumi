from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import FocusZone, toggle_focus_zone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, _cmd: RoutedCommand) -> None:
    if overlay._rt.state.focus_zone == FocusZone.TIMELINE:
        overlay.scrub.stop_key_scrub()
    overlay._rt.state = toggle_focus_zone(overlay._rt.state)
    overlay.activity.keyboard_activity()
    overlay.update()


register(Command.TOGGLE_FOCUS_ZONE, handle)
