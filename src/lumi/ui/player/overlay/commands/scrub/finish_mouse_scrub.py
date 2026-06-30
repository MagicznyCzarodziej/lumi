from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import View
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, _cmd: RoutedCommand) -> None:
    scrub = overlay._rt.state.ensure_scrub()
    scrub.seek_dragging = False
    overlay.releaseMouse()
    overlay.scrub.finish()
    if overlay._rt.state.view == View.SCRUB:
        overlay.activity.dismiss_to_watching()
    else:
        overlay.activity.show_controls()


register(Command.FINISH_MOUSE_SCRUB, handle)
