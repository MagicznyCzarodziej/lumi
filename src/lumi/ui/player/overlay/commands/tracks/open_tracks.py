from __future__ import annotations

from lumi.ui.player.overlay.commands.processor import register, show_panel
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import open_tracks, selected_track_index
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle(overlay: PlayerOverlay, cmd: RoutedCommand) -> None:
    if not cmd.track_kind:
        return
    show_panel(overlay)
    overlay._rt.state = open_tracks(overlay._rt.state, cmd.track_kind)
    overlay.tracks.refresh_rows()
    overlay._rt.state.track_focus = selected_track_index(
        overlay._rt.state, overlay._rt.controller.current_sid(), overlay._rt.controller.current_aid()
    )
    overlay.panel.rebuild()
    overlay.panel.ensure_panel_focus_visible()
    overlay.activity.sync_cursor()
    overlay.update()


register(Command.OPEN_TRACKS, handle)
