from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.subtitles.discovery import discover_subtitle_files
from lumi.domain.subtitles.sidecar_path import subtitle_sidecar_path
from lumi.domain.subtitles.browse import share_path
from lumi.domain.video_aspect import VIDEO_ASPECT_MODES
from lumi.infrastructure.track_selection import SavedTrackSelection, load_track_selection, save_track_selection
from lumi.ui.player.overlay.services.base import OverlayService
from lumi.ui.player.overlay.state import TrackKind, TrackRow, View, track_row_actions


class TrackService(OverlayService):
    def persist_track_selection(self) -> None:
        library_path = self._rt.library_path
        if library_path is None:
            return
        sid = self._rt.controller.current_sid()
        save_track_selection(
            library_path,
            SavedTrackSelection(
                aid=self._rt.controller.current_aid(),
                sid=sid,
                subtitle_off=sid is None,
                subtitle_label=(
                    None if sid is None else self._rt.controller.current_subtitle_label()
                ),
                subtitle_path=self._persisted_subtitle_path() if sid is not None else None,
            ),
        )

    def _persisted_subtitle_path(self) -> PurePosixPath | None:
        sid = self._rt.controller.current_sid()
        if sid is None:
            return None
        if self._rt.selected_subtitle_path is not None:
            return self._rt.selected_subtitle_path
        stored = self._rt.controller.subtitle_share_path(sid)
        if stored is not None:
            return stored
        return self.guess_subtitle_path_from_label(self._rt.controller.current_subtitle_label())

    def guess_subtitle_path_from_label(self, label: str | None) -> PurePosixPath | None:
        if not label or self._rt.library_path is None:
            return None
        sidecar = subtitle_sidecar_path(self._rt.library_path)
        if sidecar.name == label:
            return share_path(sidecar)
        if self._rt.deps.files_lister is not None and set(self._rt.deps.subtitle_extensions):
            for path in discover_subtitle_files(
                self._rt.deps.files_lister,
                self._rt.library_path,
                set(self._rt.deps.subtitle_extensions),
                library_root=self._rt.deps.library_root,
                video_extensions=set(self._rt.deps.video_extensions),
            ):
                if path.name == label:
                    return share_path(path)
        return None

    def resolve_subtitle_share_path(self, path: PurePosixPath) -> PurePosixPath:
        resolver = self._rt.deps.playback_uri_resolver
        if resolver is None:
            raise OSError("No playback resolver")
        return resolver.resolve_share_file(share_path(path))

    def maybe_persist_selection(self) -> None:
        if not self._rt.restoring_track_selection:
            self.persist_track_selection()

    def on_track_list_changed(self) -> None:
        self.refresh_rows()
        self._o.playback.maybe_restore_state()

    def _subtitle_tracks_excluding_off(self) -> list[tuple[int, str]]:
        return [
            (track_id, label)
            for track_id, label in self._rt.controller.subtitle_tracks()
            if track_id is not None
        ]

    def restore_selection(self) -> bool:
        library_path = self._rt.library_path
        if library_path is None:
            return True
        saved = load_track_selection(library_path)
        if saved is None:
            return True

        self._rt.restoring_track_selection = True
        try:
            if saved.aid is not None:
                for track_id, _ in self._rt.controller.audio_tracks():
                    if track_id == saved.aid:
                        self._rt.controller.set_aid(saved.aid)
                        break

            if saved.subtitle_off:
                self._rt.controller.set_sid(None)
                self._rt.selected_subtitle_path = None
                return True

            tracks = self._subtitle_tracks_excluding_off()

            if saved.subtitle_label:
                for track_id, label in tracks:
                    if label == saved.subtitle_label:
                        self._rt.controller.set_sid(track_id)
                        self._rt.selected_subtitle_path = saved.subtitle_path
                        return True

            if saved.sid is not None:
                for track_id, _ in tracks:
                    if track_id == saved.sid:
                        self._rt.controller.set_sid(track_id)
                        self._rt.selected_subtitle_path = saved.subtitle_path
                        return True

            if saved.subtitle_path is not None:
                if self.apply_saved_subtitle_path(saved.subtitle_path):
                    return True
                return False

            guessed = self.guess_subtitle_path_from_label(saved.subtitle_label)
            if guessed is not None and self.apply_saved_subtitle_path(guessed):
                return True

            if not tracks and (saved.subtitle_label or saved.sid is not None):
                return False
        finally:
            self._rt.restoring_track_selection = False
            self.refresh_rows()
            self._update()
        return True

    def apply_saved_subtitle_path(self, path: PurePosixPath) -> bool:
        library_path = self._rt.library_path
        if library_path is None:
            return False

        sidecar = subtitle_sidecar_path(library_path)
        normalized = share_path(path)
        is_sidecar = normalized == share_path(sidecar) or normalized.name == sidecar.name
        if (
            is_sidecar
            and self._rt.deps.subtitle_cache is not None
            and self._rt.deps.subtitle_cache.contains(library_path)
        ):
            local = self._rt.deps.subtitle_cache.local_path(library_path)
            if local is not None:
                self._rt.selected_subtitle_path = share_path(sidecar)
                self._o.subtitles.load_cached_napi(local)
                return self._rt.controller.current_sid() is not None

        if self._rt.deps.playback_uri_resolver is None:
            return False
        try:
            resolved = self.resolve_subtitle_share_path(normalized)
            if self._o.subtitles.read_share_file_bytes(resolved) is None:
                return False
        except OSError:
            return False

        self._rt.selected_subtitle_path = normalized
        self._o.subtitles.load_external(normalized)
        return self._rt.controller.current_sid() is not None

    def refresh_rows(self):
        if self._rt.state.track_kind == TrackKind.SUBTITLES:
            library_path = self._rt.library_path
            cache_exists = (
                library_path is not None
                and self._rt.deps.subtitle_cache is not None
                and self._rt.deps.subtitle_cache.contains(library_path)
            )
            saved_to_nas = (
                library_path is not None
                and self._rt.deps.napi_saved_state is not None
                and self._rt.deps.napi_saved_state.is_saved_to_nas(library_path)
            )
            show_napi_actions = cache_exists and not saved_to_nas
            rows = []
            for track_id, label in self._rt.controller.subtitle_tracks():
                is_napi = self._rt.controller.is_napi_track(track_id)
                rows.append(
                    TrackRow(
                        label=label,
                        mpv_id=track_id,
                        show_napi_save=is_napi and show_napi_actions,
                        show_napi_delete=is_napi and show_napi_actions,
                    )
                )
            footer: list[TrackRow] = []
            if self._rt.controller.current_sid() is not None:
                footer.append(
                    TrackRow(label="Delay", is_action=True, is_sub_delay_control=True)
                )
            if self._rt.deps.napi_available and library_path is not None:
                if self._rt.napi_downloading:
                    footer.append(TrackRow(label="Downloading…", is_action=True))
                elif self._rt.napi_status_message:
                    footer.append(
                        TrackRow(label=self._rt.napi_status_message, is_action=True)
                    )
                    footer.append(
                        TrackRow(label="Download from NapiProjekt", opens_napi_download=True, is_action=True)
                    )
                else:
                    footer.append(
                        TrackRow(label="Download from NapiProjekt", opens_napi_download=True, is_action=True)
                    )
            if self._rt.deps.files_lister is not None:
                footer.append(TrackRow(label="Browse subtitles", opens_browse=True, is_action=True))
            rows.extend(footer)
            self._rt.state.track_rows = rows
            if self._rt.state.track_action_focus is not None:
                if self._rt.state.track_focus >= len(rows):
                    self._rt.state.track_action_focus = None
                else:
                    actions = track_row_actions(rows[self._rt.state.track_focus])
                    if self._rt.state.track_action_focus not in actions:
                        self._rt.state.track_action_focus = None
        else:
            self._rt.state.track_rows = [
                TrackRow(label=label, mpv_id=track_id)
                for track_id, label in self._rt.controller.audio_tracks()
            ]
        if self._rt.state.view in (View.CONTROLS, View.TRACKS):
            self._update()

    def select_video_aspect(self, index: int) -> None:
        if index < 0 or index >= len(VIDEO_ASPECT_MODES):
            return
        self._rt.controller.set_video_aspect_mode(VIDEO_ASPECT_MODES[index])
        self._rt.state.video_focus = index
        self._o.playback.persist_video_aspect()
        self._o.activity.note_ui_activity()
        self._update()

    def select(self, index: int):
        rows = self._rt.state.track_rows or []
        if index < 0 or index >= len(rows):
            return
        row = rows[index]
        if self._rt.state.track_kind == TrackKind.SUBTITLES:
            if row.opens_browse:
                self._o.browse.open()
                return
            if row.opens_napi_download:
                self._o.napi.start_download()
                return
            if row.is_action:
                return
            self._rt.selected_subtitle_path = self._rt.controller.subtitle_share_path(row.mpv_id)
            self._rt.controller.set_sid(row.mpv_id)
        else:
            self._rt.controller.set_aid(row.mpv_id)
        self.refresh_rows()
        self.maybe_persist_selection()
        self._update()
