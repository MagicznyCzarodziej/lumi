from __future__ import annotations
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.state import TrackKind

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

def handle_hit(overlay: PlayerOverlay, key: str) -> None:
    if key == "m1":
        overlay._rt.controller.seek_relative(-1)
    elif key == "center":
        overlay._rt.controller.toggle_pause()
    elif key == "p1":
        overlay._rt.controller.seek_relative(1)
    elif key == "prev_ep":
        overlay.playback.play_adjacent_episode(previous=True)
        return
    elif key == "next_ep":
        overlay.playback.play_adjacent_episode(previous=False)
        return
    elif key == "subs":
        from lumi.ui.player.overlay.commands.processor import process_command

        process_command(overlay, RoutedCommand(Command.OPEN_TRACKS, track_kind=TrackKind.SUBTITLES))
        return
    elif key == "audio":
        from lumi.ui.player.overlay.commands.processor import process_command

        process_command(overlay, RoutedCommand(Command.OPEN_TRACKS, track_kind=TrackKind.AUDIO))
        return
    elif key == "video":
        from lumi.ui.player.overlay.commands.processor import process_command

        process_command(overlay, RoutedCommand(Command.OPEN_VIDEO))
        return
    elif key.startswith("video:"):
        overlay.tracks.select_video_aspect(int(key.split(":")[1]))
        return
    elif key.startswith("track:"):
        if key.endswith(":save"):
            overlay.napi.start_save()
            return
        if key.endswith(":delete"):
            overlay.napi.delete_subtitle()
            return
        if key.endswith(":delay-earlier"):
            overlay.subtitles.adjust_delay(-1)
            return
        if key.endswith(":delay-later"):
            overlay.subtitles.adjust_delay(1)
            return
        overlay.tracks.select(int(key.split(":")[1]))
        return
    elif key.startswith("browse:"):
        overlay.browse.activate_row(int(key.split(":")[1]))
        overlay.update()
        return
    overlay.playback.sync_to_scrub()
    overlay.activity.show_controls()
