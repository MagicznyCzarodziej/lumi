from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, _cmd: RoutedCommand) -> None:
    action = overlay._rt.state.track_action_focus
    if action == "save":
        overlay.napi.start_save()
    elif action == "delete":
        overlay.napi.delete_subtitle()
    overlay.activity.note_ui_activity()


register(Command.ACTIVATE_TRACK_ACTION, handle)
