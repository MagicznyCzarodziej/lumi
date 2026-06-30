from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register, refresh_panel, show_panel
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import open_video
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, _cmd: RoutedCommand) -> None:
    show_panel(overlay)
    focus = overlay._rt.controller.video_aspect_mode_index()
    overlay._rt.state = open_video(overlay._rt.state, focus_index=focus)
    refresh_panel(overlay)
    overlay.activity.sync_cursor()


register(Command.OPEN_VIDEO, handle)
