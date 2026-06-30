from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import QTimer

from lumi.domain.library.episode_navigation import find_episode_display_name, find_episode_neighbors
from lumi.domain.video_aspect import VideoAspectMode
from lumi.infrastructure.video_aspect_preferences import load_video_aspect, save_video_aspect
from lumi.ui.player.controller.events import PlaybackState
from lumi.ui.player.overlay.services.base import OverlayService
from lumi.ui.player.overlay.state import View, cross_order


class PlaybackService(OverlayService):
    def on_playback_state(self, playback: PlaybackState):
        prev_vol = self._rt.state.volume
        prev_muted = self._rt.state.muted
        self._rt.state.volume = playback.volume
        self._rt.state.muted = playback.muted
        self._rt.state.paused = playback.paused
        scrub = self._rt.state.ensure_scrub()
        if not scrub.is_scrubbing():
            self._rt.state.time_pos = playback.time_pos
            scrub.time_pos = playback.time_pos
            if playback.duration > 0:
                scrub.scrub_fraction = playback.time_pos / playback.duration
        self._rt.state.duration = playback.duration
        scrub.duration = playback.duration
        if not self._rt.volume_baseline_set:
            self._rt.volume_baseline_set = True
        elif abs(playback.volume - prev_vol) > 0.5 or playback.muted != prev_muted:
            self._o.volume.flash()
            return
        if self._o.activity.ui_anim_active():
            return
        if self._rt.state.view in (View.WATCHING, View.SCRUB):
            if self._rt.state.view == View.SCRUB:
                self._update()
            return
        self._update()

    def sync_to_scrub(self):
        time_pos = self._rt.controller.time_pos()
        duration = self._rt.controller.duration()
        scrub = self._rt.state.ensure_scrub()
        self._rt.state.time_pos = time_pos
        self._rt.state.duration = duration
        self._rt.state.paused = self._rt.controller.is_paused()
        scrub.time_pos = time_pos
        scrub.duration = duration
        if duration > 0:
            scrub.scrub_fraction = time_pos / duration

    def persist_video_aspect(self) -> None:
        library_path = self._rt.library_path
        if library_path is None:
            return
        save_video_aspect(library_path, self._rt.controller.video_aspect_mode())

    def _restore_video_aspect(self) -> None:
        library_path = self._rt.library_path
        if library_path is None:
            return
        saved = load_video_aspect(library_path)
        mode = saved if saved is not None else VideoAspectMode.AUTO
        self._rt.controller.set_video_aspect_mode(mode)
        self._rt.state.video_focus = self._rt.controller.video_aspect_mode_index()

    def maybe_restore_state(self) -> None:
        if self._rt.library_path is None or not self._rt.controller.has_media():
            return
        if self._rt.pending_aspect_restore:
            self._restore_video_aspect()
            self._rt.pending_aspect_restore = False
        if (
            not self._rt.pending_track_restore
            or self._rt.restoring_track_selection
        ):
            return
        if self._o.tracks.restore_selection():
            self._rt.pending_track_restore = False

    def set_media_info(
        self,
        stream_uri: str,
        library_path: PurePosixPath | None = None,
        *,
        resolved_video_path: PurePosixPath | None = None,
    ):
        self._rt.library_path = library_path
        self._rt.resolved_video_path = resolved_video_path
        self._rt.stream_uri = stream_uri
        self._rt.selected_subtitle_path = None
        self._rt.pending_track_restore = library_path is not None
        self._rt.pending_aspect_restore = library_path is not None
        self._rt.restoring_track_selection = False
        self._rt.browse_target = None
        self._rt.browse_busy = False
        self._rt.napi_downloading = False
        self._rt.napi_saving = False
        self._rt.napi_status_message = None
        self._rt.volume_baseline_set = False
        self._rt.state.volume_flash = False
        self._rt.prev_episode_path = None
        self._rt.next_episode_path = None
        self._rt.episode_title = None
        if library_path is not None and self._rt.deps.library_repository is not None:
            entries = self._rt.deps.library_repository.get_top_level_entries()
            neighbors = find_episode_neighbors(entries, library_path)
            self._rt.prev_episode_path = neighbors.previous
            self._rt.next_episode_path = neighbors.next
            self._rt.state.prev_ep_available = neighbors.previous is not None
            self._rt.state.next_ep_available = neighbors.next is not None
            self._rt.episode_title = find_episode_display_name(entries, library_path)
        else:
            self._rt.state.prev_ep_available = False
            self._rt.state.next_ep_available = False
        order = cross_order(
            prev_ep=self._rt.state.prev_ep_available,
            next_ep=self._rt.state.next_ep_available,
        )
        if self._rt.state.cross_focus not in order:
            self._rt.state.cross_focus = "center"
        self._rt.volume_hide_timer.stop()
        self._o.scrub.stop_key_scrub(finalize=False)
        self._rt.state.scrub = None
        self._rt.state.time_pos = 0.0
        self._rt.state.duration = 0.0
        self._rt.controller.notify_media_loaded()
        self._o.activity.sync_cursor()
        QTimer.singleShot(0, self.maybe_restore_state)
        self._update()

    def play_adjacent_episode(self, *, previous: bool) -> None:
        path = self._rt.prev_episode_path if previous else self._rt.next_episode_path
        play = self._rt.deps.on_play_path
        if path is None or play is None:
            return
        play(path)
