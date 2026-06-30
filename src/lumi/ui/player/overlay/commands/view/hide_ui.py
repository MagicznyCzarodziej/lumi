from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import View, close_tracks, close_video
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, _cmd: RoutedCommand) -> None:
    overlay.scrub.stop_key_scrub()
    if overlay._rt.state.view == View.SUBTITLE_BROWSE:
        overlay.browse.back()
    elif overlay._rt.state.view == View.TRACKS:
        overlay._rt.state = close_tracks(overlay._rt.state)
        overlay.activity.show_controls()
    elif overlay._rt.state.view == View.VIDEO:
        overlay._rt.state = close_video(overlay._rt.state)
        overlay.activity.show_controls()
    elif overlay._rt.state.view == View.WATCHING and overlay._rt.deps.on_close is not None:
        overlay._rt.deps.on_close()
    else:
        overlay.activity.dismiss_to_watching()


register(Command.HIDE_UI, handle)
