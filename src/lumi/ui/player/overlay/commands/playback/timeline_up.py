from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import FocusZone, View
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, _cmd: RoutedCommand) -> None:
    overlay.scrub.stop_key_scrub()
    if overlay._rt.state.view == View.SCRUB:
        overlay.activity.show_controls()
    overlay._rt.state = overlay._rt.state.__class__(
        **{**overlay._rt.state.__dict__, "focus_zone": FocusZone.CONTROLS}
    )
    overlay.update()
    overlay.activity.keyboard_activity()


register(Command.TIMELINE_UP, handle)
