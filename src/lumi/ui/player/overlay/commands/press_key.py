from __future__ import annotations
from lumi.ui.player.overlay.input_router import Command, RoutedCommand

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def press_key_for_command(overlay: PlayerOverlay, cmd: RoutedCommand) -> str | None:
    if cmd.command == Command.HIT:
        if cmd.hit_key in ("subs", "audio", "video"):
            return None
        return cmd.hit_key
    if cmd.command == Command.ACTIVATE_CROSS:
        return overlay._rt.state.cross_focus
    if cmd.command == Command.TOGGLE_PAUSE:
        return "center"
    if cmd.command == Command.SELECT_TRACK:
        return f"track:{cmd.track_index}"
    if cmd.command == Command.ACTIVATE_TRACK_ACTION:
        action = overlay._rt.state.track_action_focus
        if action is not None:
            return f"track:{overlay._rt.state.track_focus}:{action}"
    if cmd.command == Command.ACTIVATE_BROWSE:
        return f"browse:{cmd.browse_index}"
    if cmd.command == Command.SELECT_VIDEO_ASPECT:
        return f"video:{cmd.video_aspect_index}"
    if cmd.command == Command.OPEN_FILE:
        return "open"
    return None
