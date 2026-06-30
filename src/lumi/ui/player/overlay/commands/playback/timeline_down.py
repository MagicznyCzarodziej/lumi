from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, _cmd: RoutedCommand) -> None:
    overlay.scrub.stop_key_scrub()
    overlay.activity.dismiss_to_watching()
    overlay.activity.keyboard_activity()


register(Command.TIMELINE_DOWN, handle)
