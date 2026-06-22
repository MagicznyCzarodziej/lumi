"""Transparent overlay widget — wiring only."""

from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QElapsedTimer, QPoint, Qt, QThreadPool, QTimer
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QWheelEvent
from PySide6.QtWidgets import QMessageBox, QSizePolicy, QWidget

from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.file_writer import FileWriter
from lumi.domain.filesystem.files_lister import FilesLister
from lumi.domain.filesystem.video_range_reader import VideoRangeReader
from lumi.domain.playback import PlaybackUriResolver
from lumi.domain.subtitles.cache import SubtitleCache
from lumi.domain.subtitles.provider import SubtitleDownloadProvider
from lumi.domain.subtitles.saved_state import NapiSavedStateStore
from lumi.domain.subtitles.sidecar_path import subtitle_sidecar_path
from lumi.domain.subtitles.discovery import discover_subtitle_files
from lumi.domain.video_aspect import VIDEO_ASPECT_MODES, VideoAspectMode, video_aspect_label
from lumi.infrastructure.track_selection import SavedTrackSelection, load_track_selection, save_track_selection
from lumi.infrastructure.video_aspect_preferences import load_video_aspect, save_video_aspect
from lumi.ui.player.controller.controller import MpvController
from lumi.ui.player.controller.events import PlaybackState
from lumi.ui.player.controller.scrub_engine import ScrubEngine
from lumi.ui.player.controller.volume_engine import VolumeEngine
from lumi.ui.player.overlay.input_router import Command, InputRouter, RoutedCommand
from lumi.domain.subtitles.browse import BrowseEntryKind, BrowseRow, parent_directory, share_path
from lumi.ui.player.overlay.layout.regions import compute_layout
from lumi.ui.player.overlay.layout.panel_scroll import scroll_to_show_item
from lumi.ui.player.overlay.paint.browse import paint_browse_sheet
from lumi.ui.player.overlay.paint.controls import paint_corner_hints, paint_cross_controls, paint_timeline
from lumi.ui.player.overlay.paint.tracks import paint_track_sheet
from lumi.ui.player.overlay.paint.video import paint_video_sheet
from lumi.ui.player.overlay.paint.volume import paint_volume
from lumi.ui.player.overlay.press_animation import PressAnimation, press_strength, release
from lumi.ui.player.overlay.state import (
    CROSS_ORDER,
    FocusZone,
    OverlayState,
    TrackKind,
    TrackRow,
    View,
    close_subtitle_browse,
    close_tracks,
    close_video,
    dismiss_controls,
    hide_controls,
    move_cross_focus,
    move_track_action_focus,
    move_track_focus,
    move_video_focus,
    open_subtitle_browse,
    open_tracks,
    open_video,
    selected_track_index,
    show_controls,
    show_scrub,
    toggle_focus_zone,
    track_row_actions,
)
from lumi.ui.workers.directory_list_worker import DirectoryListWorker
from lumi.ui.workers.napi_download_worker import NapiDownloadWorker
from lumi.ui.workers.napi_save_worker import NapiSaveWorker

logger = logging.getLogger(__name__)


class PlayerOverlay(QWidget):
    PRE_HIDE_FADE_MS = 1000
    FADED_OPACITY = 0.75
    HIDE_MS = 3500
    VOLUME_HIDE_MS = 2000
    PRESS_ANIM_MS = 16

    def __init__(
        self,
        controller: MpvController,
        *,
        files_lister: FilesLister | None = None,
        playback_uri_resolver: PlaybackUriResolver | None = None,
        library_root: PurePosixPath | None = None,
        video_extensions: set[str] | None = None,
        subtitle_extensions: set[str] | None = None,
        subtitle_cache: SubtitleCache | None = None,
        napi_provider: SubtitleDownloadProvider | None = None,
        napi_saved_state: NapiSavedStateStore | None = None,
        video_reader: VideoRangeReader | None = None,
        file_repository: FileRepository | None = None,
        file_writer: FileWriter | None = None,
        napi_enabled: bool = False,
        napi_language: str = "ENG",
        on_close: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._controller = controller
        self._files_lister = files_lister
        self._playback_uri_resolver = playback_uri_resolver
        self._library_root = library_root
        self._video_extensions = video_extensions or set()
        self._subtitle_extensions = subtitle_extensions or set()
        self._subtitle_cache = subtitle_cache
        self._napi_provider = napi_provider
        self._napi_saved_state = napi_saved_state
        self._video_reader = video_reader
        self._file_repository = file_repository
        self._file_writer = file_writer
        self._napi_enabled = napi_enabled and napi_provider is not None and subtitle_cache is not None
        self._napi_language = napi_language
        self._napi_downloading = False
        self._napi_saving = False
        self._napi_status_message: str | None = None
        self._on_close = on_close
        self._router = InputRouter()
        self._state = OverlayState()
        self._layout = compute_layout(1280, 720, View.WATCHING, TrackKind.SUBTITLES, [])
        self._library_path: PurePosixPath | None = None
        self._resolved_video_path: PurePosixPath | None = None
        self._stream_uri: str | None = None
        self._selected_subtitle_path: PurePosixPath | None = None
        self._pending_track_restore = False
        self._pending_aspect_restore = False
        self._restoring_track_selection = False
        self._browse_target: PurePosixPath | None = None
        self._browse_busy = False
        self._thread_pool = QThreadPool.globalInstance()
        self._key_scrub_timer = QElapsedTimer()
        self._volume_adjust_timer = QElapsedTimer()
        self._volume_adjust_direction = 0
        self._volume_step_base = 1
        self._ui_opacity = 1.0
        self._hide_timer = QTimer(self)
        self._dim_timer = QTimer(self)
        self._volume_hide_timer = QTimer(self)
        self._seek_apply_timer = QTimer(self)
        self._key_scrub_tick_timer = QTimer(self)
        self._volume_adjust_tick_timer = QTimer(self)
        self._press_anim_timer = QTimer(self)
        self._press_anim: PressAnimation | None = None
        self._press_clock = QElapsedTimer()
        self._volume_baseline_set = False
        self._hide_timer.setSingleShot(True)
        self._dim_timer.setSingleShot(True)
        self._volume_hide_timer.setSingleShot(True)
        self._seek_apply_timer.setSingleShot(True)
        self._key_scrub_tick_timer.setInterval(33)
        self._volume_adjust_tick_timer.setInterval(33)
        self._press_anim_timer.setInterval(self.PRESS_ANIM_MS)
        self._press_anim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._hide_timer.timeout.connect(self._on_hide_timeout)
        self._dim_timer.timeout.connect(self._on_pre_hide_dim)
        self._volume_hide_timer.timeout.connect(self._on_volume_hide)
        self._seek_apply_timer.timeout.connect(self._apply_pending_seek)
        self._key_scrub_tick_timer.timeout.connect(self._on_key_scrub_tick)
        self._volume_adjust_tick_timer.timeout.connect(self._on_volume_adjust_tick)
        self._press_anim_timer.timeout.connect(self._on_press_anim_tick)
        self._controller.signals.state_changed.connect(self._on_playback_state)
        self._controller.signals.track_list_changed.connect(self._on_track_list_changed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    @property
    def state(self) -> OverlayState:
        return self._state

    def bind(self):
        self._controller.bind()

    def unbind(self):
        self._hide_timer.stop()
        self._dim_timer.stop()
        self._volume_hide_timer.stop()
        self._seek_apply_timer.stop()
        self._key_scrub_tick_timer.stop()
        self._volume_adjust_tick_timer.stop()
        self._volume_adjust_direction = 0
        self._press_anim_timer.stop()
        self._press_anim = None
        self._controller.unbind()
        self.unsetCursor()
        if parent := self.parentWidget():
            parent.unsetCursor()

    def close_if_watching(self) -> bool:
        if self._state.view == View.WATCHING and self._on_close is not None:
            self._on_close()
            return True
        return False

    def _dismiss_to_watching(self) -> None:
        self._stop_key_scrub()
        self._state = dismiss_controls(self._state)
        self._hide_timer.stop()
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        self._sync_cursor()
        self._sync_overlay_visibility()
        self.update()

    def show_scrubber(self) -> None:
        self.show()
        self.raise_()
        self._state = show_scrub(self._state)
        self._sync_playback_to_scrub()
        self._hide_timer.stop()
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        self.setFocus()
        self._sync_cursor()
        self.update()

    def show_controls(self):
        self.show()
        self.raise_()
        self._state = show_controls(self._state)
        self._sync_playback_to_scrub()
        self._note_ui_activity()
        self.setFocus()
        self._sync_cursor()
        self.update()

    def start_watching(self) -> None:
        """Hide overlay so the OpenGL video layer is visible (required on macOS)."""
        self._state = hide_controls(self._state)
        self._hide_timer.stop()
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        self._sync_cursor()
        self._sync_overlay_visibility()

    def _sync_overlay_visibility(self) -> None:
        if self._state.view == View.WATCHING and not self._state.volume_flash:
            self.hide()
            parent = self.parentWidget()
            if parent is not None and hasattr(parent, "mpv_widget"):
                parent.mpv_widget.raise_()
        else:
            self.show()
            self.raise_()

    def set_media_info(
        self,
        stream_uri: str,
        library_path: PurePosixPath | None = None,
        *,
        resolved_video_path: PurePosixPath | None = None,
    ):
        self._library_path = library_path
        self._resolved_video_path = resolved_video_path
        self._stream_uri = stream_uri
        self._selected_subtitle_path = None
        self._pending_track_restore = library_path is not None
        self._pending_aspect_restore = library_path is not None
        self._restoring_track_selection = False
        self._browse_target = None
        self._browse_busy = False
        self._napi_downloading = False
        self._napi_saving = False
        self._napi_status_message = None
        self._volume_baseline_set = False
        self._state.volume_flash = False
        self._volume_hide_timer.stop()
        self._stop_key_scrub(finalize=False)
        self._state.scrub = None
        self._state.time_pos = 0.0
        self._state.duration = 0.0
        self._controller.notify_media_loaded()
        self._sync_cursor()
        QTimer.singleShot(0, self._maybe_restore_playback_state)
        self.update()

    def _on_playback_state(self, playback: PlaybackState):
        prev_vol = self._state.volume
        prev_muted = self._state.muted
        self._state.volume = playback.volume
        self._state.muted = playback.muted
        self._state.paused = playback.paused
        scrub = self._state.ensure_scrub()
        if not scrub.is_scrubbing():
            self._state.time_pos = playback.time_pos
            scrub.time_pos = playback.time_pos
            if playback.duration > 0:
                scrub.scrub_fraction = playback.time_pos / playback.duration
        self._state.duration = playback.duration
        scrub.duration = playback.duration
        if not self._volume_baseline_set:
            self._volume_baseline_set = True
        elif abs(playback.volume - prev_vol) > 0.5 or playback.muted != prev_muted:
            self._flash_volume()
            return
        if self._ui_anim_active():
            return
        if self._state.view in (View.WATCHING, View.SCRUB):
            if self._state.view == View.SCRUB:
                self.update()
            return
        self.update()

    def _sync_playback_to_scrub(self):
        time_pos = self._controller.time_pos()
        duration = self._controller.duration()
        scrub = self._state.ensure_scrub()
        self._state.time_pos = time_pos
        self._state.duration = duration
        self._state.paused = self._controller.is_paused()
        scrub.time_pos = time_pos
        scrub.duration = duration
        if duration > 0:
            scrub.scrub_fraction = time_pos / duration

    def persist_track_selection(self) -> None:
        library_path = self._library_path
        if library_path is None:
            return
        sid = self._controller.current_sid()
        save_track_selection(
            library_path,
            SavedTrackSelection(
                aid=self._controller.current_aid(),
                sid=sid,
                subtitle_off=sid is None,
                subtitle_label=(
                    None if sid is None else self._controller.current_subtitle_label()
                ),
                subtitle_path=self._persisted_subtitle_path() if sid is not None else None,
            ),
        )

    def _persisted_subtitle_path(self) -> PurePosixPath | None:
        sid = self._controller.current_sid()
        if sid is None:
            return None
        if self._selected_subtitle_path is not None:
            return self._selected_subtitle_path
        stored = self._controller.subtitle_share_path(sid)
        if stored is not None:
            return stored
        return self._guess_subtitle_path_from_label(self._controller.current_subtitle_label())

    def _guess_subtitle_path_from_label(self, label: str | None) -> PurePosixPath | None:
        if not label or self._library_path is None:
            return None
        sidecar = subtitle_sidecar_path(self._library_path)
        if sidecar.name == label:
            return share_path(sidecar)
        if self._files_lister is not None and self._subtitle_extensions:
            for path in discover_subtitle_files(
                self._files_lister,
                self._library_path,
                self._subtitle_extensions,
                library_root=self._library_root,
                video_extensions=self._video_extensions,
            ):
                if path.name == label:
                    return share_path(path)
        return None

    def _resolve_subtitle_share_path(self, path: PurePosixPath) -> PurePosixPath:
        resolver = self._playback_uri_resolver
        if resolver is None:
            raise OSError("No playback resolver")
        return resolver.resolve_share_file(share_path(path))

    def persist_video_aspect(self) -> None:
        library_path = self._library_path
        if library_path is None:
            return
        save_video_aspect(library_path, self._controller.video_aspect_mode())

    def _maybe_persist_track_selection(self) -> None:
        if not self._restoring_track_selection:
            self.persist_track_selection()

    def _restore_video_aspect(self) -> None:
        library_path = self._library_path
        if library_path is None:
            return
        saved = load_video_aspect(library_path)
        mode = saved if saved is not None else VideoAspectMode.AUTO
        self._controller.set_video_aspect_mode(mode)
        self._state.video_focus = self._controller.video_aspect_mode_index()

    def _maybe_restore_playback_state(self) -> None:
        if self._library_path is None or not self._controller.has_media():
            return
        if self._pending_aspect_restore:
            self._restore_video_aspect()
            self._pending_aspect_restore = False
        if (
            not self._pending_track_restore
            or self._restoring_track_selection
        ):
            return
        if self._restore_track_selection():
            self._pending_track_restore = False

    def _on_track_list_changed(self) -> None:
        self._refresh_track_rows()
        self._maybe_restore_playback_state()

    def _subtitle_tracks_excluding_off(self) -> list[tuple[int, str]]:
        return [
            (track_id, label)
            for track_id, label in self._controller.subtitle_tracks()
            if track_id is not None
        ]

    def _restore_track_selection(self) -> bool:
        library_path = self._library_path
        if library_path is None:
            return True
        saved = load_track_selection(library_path)
        if saved is None:
            return True

        self._restoring_track_selection = True
        try:
            if saved.aid is not None:
                for track_id, _ in self._controller.audio_tracks():
                    if track_id == saved.aid:
                        self._controller.set_aid(saved.aid)
                        break

            if saved.subtitle_off:
                self._controller.set_sid(None)
                self._selected_subtitle_path = None
                return True

            tracks = self._subtitle_tracks_excluding_off()

            if saved.subtitle_label:
                for track_id, label in tracks:
                    if label == saved.subtitle_label:
                        self._controller.set_sid(track_id)
                        self._selected_subtitle_path = saved.subtitle_path
                        return True

            if saved.sid is not None:
                for track_id, _ in tracks:
                    if track_id == saved.sid:
                        self._controller.set_sid(track_id)
                        self._selected_subtitle_path = saved.subtitle_path
                        return True

            if saved.subtitle_path is not None:
                if self._apply_saved_subtitle_path(saved.subtitle_path):
                    return True
                return False

            guessed = self._guess_subtitle_path_from_label(saved.subtitle_label)
            if guessed is not None and self._apply_saved_subtitle_path(guessed):
                return True

            if not tracks and (saved.subtitle_label or saved.sid is not None):
                return False
        finally:
            self._restoring_track_selection = False
            self._refresh_track_rows()
            self.update()
        return True

    def _apply_saved_subtitle_path(self, path: PurePosixPath) -> bool:
        library_path = self._library_path
        if library_path is None:
            return False

        sidecar = subtitle_sidecar_path(library_path)
        normalized = share_path(path)
        is_sidecar = normalized == share_path(sidecar) or normalized.name == sidecar.name
        if (
            is_sidecar
            and self._subtitle_cache is not None
            and self._subtitle_cache.contains(library_path)
        ):
            local = self._subtitle_cache.local_path(library_path)
            if local is not None:
                self._selected_subtitle_path = share_path(sidecar)
                self._load_cached_napi_subtitle(local)
                return self._controller.current_sid() is not None

        if self._playback_uri_resolver is None:
            return False
        try:
            resolved = self._resolve_subtitle_share_path(normalized)
            if self._read_share_file_bytes(resolved) is None:
                return False
        except OSError:
            return False

        self._selected_subtitle_path = normalized
        self._load_external_subtitle(normalized)
        return self._controller.current_sid() is not None

    def _refresh_track_rows(self):
        if self._state.track_kind == TrackKind.SUBTITLES:
            library_path = self._library_path
            cache_exists = (
                library_path is not None
                and self._subtitle_cache is not None
                and self._subtitle_cache.contains(library_path)
            )
            saved_to_nas = (
                library_path is not None
                and self._napi_saved_state is not None
                and self._napi_saved_state.is_saved_to_nas(library_path)
            )
            show_napi_actions = cache_exists and not saved_to_nas
            rows = []
            for track_id, label in self._controller.subtitle_tracks():
                is_napi = self._controller.is_napi_track(track_id)
                rows.append(
                    TrackRow(
                        label=label,
                        mpv_id=track_id,
                        show_napi_save=is_napi and show_napi_actions,
                        show_napi_delete=is_napi and show_napi_actions,
                    )
                )
            footer: list[TrackRow] = []
            if self._controller.current_sid() is not None:
                footer.append(
                    TrackRow(label="Delay", is_action=True, is_sub_delay_control=True)
                )
            if self._napi_enabled and library_path is not None:
                if self._napi_downloading:
                    footer.append(TrackRow(label="Downloading…", is_action=True))
                elif self._napi_status_message:
                    footer.append(
                        TrackRow(label=self._napi_status_message, is_action=True)
                    )
                    footer.append(
                        TrackRow(label="Download from NapiProjekt", opens_napi_download=True, is_action=True)
                    )
                else:
                    footer.append(
                        TrackRow(label="Download from NapiProjekt", opens_napi_download=True, is_action=True)
                    )
            if self._files_lister is not None:
                footer.append(TrackRow(label="Browse subtitles", opens_browse=True, is_action=True))
            rows.extend(footer)
            self._state.track_rows = rows
            if self._state.track_action_focus is not None:
                if self._state.track_focus >= len(rows):
                    self._state.track_action_focus = None
                else:
                    actions = track_row_actions(rows[self._state.track_focus])
                    if self._state.track_action_focus not in actions:
                        self._state.track_action_focus = None
        else:
            self._state.track_rows = [
                TrackRow(label=label, mpv_id=track_id)
                for track_id, label in self._controller.audio_tracks()
            ]
        if self._state.view in (View.CONTROLS, View.TRACKS):
            self.update()

    def _default_browse_directory(self) -> PurePosixPath | None:
        if self._library_path is not None:
            if self._playback_uri_resolver is not None:
                try:
                    resolved = self._playback_uri_resolver.resolve_path(self._library_path)
                    return share_path(resolved.parent if resolved.name else resolved)
                except OSError:
                    pass
            if self._library_path.name:
                return share_path(self._library_path.parent)
            return share_path(self._library_path)
        if self._library_root is not None and str(self._library_root).strip("/"):
            return share_path(self._library_root)
        return None

    def _open_subtitle_browse(self) -> None:
        directory = self._default_browse_directory()
        if directory is None or self._files_lister is None:
            return
        self.show()
        self.raise_()
        self._state = open_subtitle_browse(self._state)
        self._hide_timer.stop()
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        self._load_browse_directory(directory)

    def _close_subtitle_browse(self) -> None:
        self._browse_target = None
        self._browse_busy = False
        self._state = close_subtitle_browse(self._state)
        self._refresh_track_rows()
        self._rebuild_layout()
        self._note_ui_activity()
        self.update()

    def _load_browse_directory(self, directory: PurePosixPath) -> None:
        if self._files_lister is None:
            return
        self._browse_target = share_path(directory)
        self._state.browse_path = self._browse_target
        self._state.browse_rows = []
        self.update()
        if self._browse_busy:
            return
        self._start_browse_worker()

    def _start_browse_worker(self) -> None:
        if self._browse_busy or self._files_lister is None:
            return
        target = self._browse_target
        if target is None or self._state.view != View.SUBTITLE_BROWSE:
            return
        self._browse_busy = True
        worker = DirectoryListWorker(
            self._files_lister,
            target,
            self._subtitle_extensions,
            library_root=self._library_root,
        )
        worker.signals.finished.connect(
            self._on_browse_loaded,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.failed.connect(
            self._on_browse_failed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._thread_pool.start(worker)

    def _on_browse_loaded(
        self,
        requested: PurePosixPath,
        resolved: PurePosixPath,
        rows: list[BrowseRow],
    ) -> None:
        self._browse_busy = False
        if self._state.view != View.SUBTITLE_BROWSE:
            return
        if self._browse_target is not None and share_path(requested) != self._browse_target:
            self._start_browse_worker()
            return
        self._state.browse_path = share_path(resolved)
        self._state.browse_rows = list(rows)
        if self._state.browse_rows:
            self._state.browse_focus = max(
                0, min(self._state.browse_focus, len(self._state.browse_rows) - 1)
            )
        else:
            self._state.browse_focus = 0
        self._rebuild_layout()
        self._ensure_panel_focus_visible()
        self.update()
        if self._browse_target is not None and share_path(resolved) != self._browse_target:
            self._start_browse_worker()

    def _on_browse_failed(
        self,
        directory: PurePosixPath,
        message: str,
    ) -> None:
        self._browse_busy = False
        if self._state.view != View.SUBTITLE_BROWSE:
            return
        if self._browse_target is not None and share_path(directory) != self._browse_target:
            self._start_browse_worker()
            return
        logger.warning("Browse directory failed for %s: %s", directory, message)
        parent = parent_directory(share_path(directory))
        self._state.browse_rows = (
            [BrowseRow(label="..", path=parent, kind=BrowseEntryKind.PARENT)] if parent else []
        )
        self._rebuild_layout()
        self.update()
        if self._browse_target is not None and share_path(directory) != self._browse_target:
            self._start_browse_worker()

    def _browse_back(self) -> None:
        path = self._state.browse_path
        if path is None:
            self._close_subtitle_browse()
            return
        parent = parent_directory(path)
        if parent is None:
            self._close_subtitle_browse()
        else:
            self._load_browse_directory(parent)

    def _activate_browse_row(self, index: int) -> None:
        rows = self._state.browse_rows or []
        if index < 0 or index >= len(rows):
            return
        row = rows[index]
        if row.kind == BrowseEntryKind.SUBTITLE:
            self._close_subtitle_browse()
            QTimer.singleShot(0, lambda path=row.path: self._load_external_subtitle(path))
        elif row.kind in (BrowseEntryKind.DIRECTORY, BrowseEntryKind.PARENT):
            self._state.browse_focus = index
            self._load_browse_directory(row.path)
        self._note_ui_activity()

    def _rebuild_layout(self) -> None:
        rows = self._state.track_rows or []
        self._layout = compute_layout(
            self.width(),
            self.height(),
            self._state.view,
            self._state.track_kind,
            rows,
            browse_path=self._state.browse_path,
            browse_rows=self._state.browse_rows,
            panel_scroll_y=self._state.panel_scroll_y,
        )
        self._state.panel_scroll_y = self._layout.panel_scroll_y
        self._state.panel_w = self._layout.panel_w

    def _panel_focus_key(self) -> str | None:
        if self._state.view == View.TRACKS:
            return f"track:{self._state.track_focus}"
        if self._state.view == View.VIDEO:
            return f"video:{self._state.video_focus}"
        if self._state.view == View.SUBTITLE_BROWSE:
            return f"browse:{self._state.browse_focus}"
        return None

    def _ensure_panel_focus_visible(self) -> None:
        focus_key = self._panel_focus_key()
        if focus_key is None:
            return
        content_top = self._layout.panel_row_tops.get(focus_key)
        rect = self._layout.hit_regions.get(focus_key)
        if content_top is None or rect is None:
            return
        new_scroll = scroll_to_show_item(
            content_top,
            rect.height(),
            viewport_top=self._layout.panel_list_top,
            viewport_bottom=self._layout.panel_list_bottom,
            scroll_y=self._state.panel_scroll_y,
        )
        if new_scroll == self._state.panel_scroll_y:
            return
        self._state.panel_scroll_y = new_scroll
        self._rebuild_layout()

    def _scroll_panel_by(self, delta_y: int) -> None:
        if self._state.view not in (View.TRACKS, View.VIDEO, View.SUBTITLE_BROWSE):
            return
        self._rebuild_layout()
        step = max(24, self._layout.metrics.track_row_h)
        notches = delta_y // 120 if delta_y else 0
        if notches == 0:
            notches = 1 if delta_y > 0 else -1
        self._state.panel_scroll_y = max(
            0,
            min(
                self._layout.panel_scroll_max,
                self._state.panel_scroll_y - notches * step,
            ),
        )
        self._rebuild_layout()
        self._note_ui_activity()
        self.update()

    def _sync_cursor(self):
        hide = self._controller.has_media() and self._state.view == View.WATCHING
        cursor = Qt.CursorShape.BlankCursor if hide else Qt.CursorShape.ArrowCursor
        self.setCursor(cursor)
        if parent := self.parentWidget():
            parent.setCursor(cursor)

    def _flash_volume(self):
        self._state.volume_flash = True
        self._volume_hide_timer.start(self.VOLUME_HIDE_MS)
        self._sync_overlay_visibility()
        self.update()

    def _on_volume_hide(self):
        self._state.volume_flash = False
        self._sync_overlay_visibility()
        self.update()

    def _is_key_scrubbing(self) -> bool:
        scrub = self._state.scrub
        return scrub is not None and scrub.keyboard_scrubbing

    def _is_ui_interaction_blocked(self) -> bool:
        if self._is_key_scrubbing():
            return True
        if self._volume_adjust_direction != 0:
            return True
        scrub = self._state.scrub
        return scrub is not None and scrub.seek_dragging

    def _on_pre_hide_dim(self) -> None:
        if self._is_ui_interaction_blocked():
            return
        if self._state.view not in (View.CONTROLS, View.SCRUB):
            return
        self._ui_opacity = self.FADED_OPACITY
        self.update()

    def _tracks_inactivity(self) -> bool:
        return self._state.view in (
            View.CONTROLS,
            View.SCRUB,
            View.TRACKS,
            View.VIDEO,
            View.SUBTITLE_BROWSE,
        )

    def _note_ui_activity(self) -> None:
        if not self._tracks_inactivity():
            return
        if self._is_ui_interaction_blocked():
            return
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        if self._state.view in (View.CONTROLS, View.SCRUB):
            self._hide_timer.start(self.HIDE_MS)
            self._dim_timer.start(max(0, self.HIDE_MS - self.PRE_HIDE_FADE_MS))
        self.update()

    def _on_hide_timeout(self):
        if self._is_key_scrubbing():
            return
        if self._state.view == View.SCRUB:
            self._dismiss_to_watching()
            return
        self._state = hide_controls(self._state)
        self._dim_timer.stop()
        self._ui_opacity = 1.0
        self._sync_cursor()
        self._sync_overlay_visibility()
        self.update()

    def _keyboard_activity(self):
        self._note_ui_activity()

    def _press_state(self) -> tuple[str | None, float]:
        anim = self._press_anim
        if anim is None:
            return None, 0.0
        return anim.key, press_strength(anim, self._press_clock.elapsed())

    def _begin_press(self, key: str) -> None:
        self._press_anim = PressAnimation(key=key, holding=True)
        self._press_clock.start()
        if not self._press_anim_timer.isActive():
            self._press_anim_timer.start()
        self.update()

    def _end_press(self) -> None:
        if self._press_anim is None or not self._press_anim.holding:
            return
        self._press_anim = release(self._press_anim, self._press_clock.elapsed())
        if not self._press_anim_timer.isActive():
            self._press_anim_timer.start()
        self.update()

    def _on_press_anim_tick(self) -> None:
        self._sync_press_anim_clock()
        if self._press_anim is not None:
            self.repaint()
        elif self._state.volume_flash:
            self.update()

    def _sync_press_anim_clock(self) -> None:
        if self._press_anim is None:
            self._press_anim_timer.stop()
            return
        _key, strength = self._press_state()
        if not self._press_anim.holding and strength <= 0.0:
            self._press_anim = None
            self._press_anim_timer.stop()

    def _ui_anim_active(self) -> bool:
        return self._press_anim is not None or self._state.volume_flash

    def notify_repaint_tick(self) -> None:
        """Optional extra repaint when mpv renders; timer drives press animation."""
        if self._press_anim is None:
            return
        self._sync_press_anim_clock()
        if self._press_anim is not None:
            self.repaint()

    def _press_key_for_command(self, cmd: RoutedCommand) -> str | None:
        if cmd.command == Command.HIT:
            if cmd.hit_key in ("subs", "audio", "video"):
                return None
            return cmd.hit_key
        if cmd.command == Command.ACTIVATE_CROSS:
            return self._state.cross_focus
        if cmd.command == Command.TOGGLE_PAUSE:
            return "center"
        if cmd.command == Command.SELECT_TRACK:
            return f"track:{cmd.track_index}"
        if cmd.command == Command.ACTIVATE_TRACK_ACTION:
            action = self._state.track_action_focus
            if action is not None:
                return f"track:{self._state.track_focus}:{action}"
        if cmd.command == Command.ACTIVATE_BROWSE:
            return f"browse:{cmd.browse_index}"
        if cmd.command == Command.SELECT_VIDEO_ASPECT:
            return f"video:{cmd.video_aspect_index}"
        if cmd.command == Command.OPEN_FILE:
            return "open"
        return None

    def _execute(self, cmd: RoutedCommand):
        c = cmd.command
        if c == Command.TOGGLE_PAUSE:
            self._controller.toggle_pause()
            if self._state.view == View.SCRUB:
                self._keyboard_activity()
                self.update()
            else:
                self.show_controls()
                self._keyboard_activity()
        elif c == Command.SHOW_CONTROLS:
            self.show_controls()
        elif c == Command.DISMISS_CONTROLS:
            self._dismiss_to_watching()
        elif c == Command.HIDE_UI:
            self._stop_key_scrub()
            if self._state.view == View.SUBTITLE_BROWSE:
                self._browse_back()
            elif self._state.view == View.TRACKS:
                self._state = close_tracks(self._state)
                self.show_controls()
            elif self._state.view == View.VIDEO:
                self._state = close_video(self._state)
                self.show_controls()
            elif self._state.view == View.WATCHING and self._on_close is not None:
                self._on_close()
            else:
                self._dismiss_to_watching()
        elif c == Command.OPEN_TRACKS and cmd.track_kind:
            self.show()
            self.raise_()
            self._state = open_tracks(self._state, cmd.track_kind)
            self._hide_timer.stop()
            self._dim_timer.stop()
            self._ui_opacity = 1.0
            self._refresh_track_rows()
            self._state.track_focus = selected_track_index(
                self._state, self._controller.current_sid(), self._controller.current_aid()
            )
            self._rebuild_layout()
            self._ensure_panel_focus_visible()
            self._sync_cursor()
            self.update()
        elif c == Command.CLOSE_TRACKS:
            self._state = close_tracks(self._state)
            self.show_controls()
        elif c == Command.OPEN_VIDEO:
            self.show()
            self.raise_()
            focus = self._controller.video_aspect_mode_index()
            self._state = open_video(self._state, focus_index=focus)
            self._hide_timer.stop()
            self._dim_timer.stop()
            self._ui_opacity = 1.0
            self._rebuild_layout()
            self._ensure_panel_focus_visible()
            self._sync_cursor()
            self.update()
        elif c == Command.CLOSE_VIDEO:
            self._state = close_video(self._state)
            self.show_controls()
        elif c == Command.MOVE_VIDEO_FOCUS:
            self._state = move_video_focus(self._state, cmd.delta)
            self._rebuild_layout()
            self._ensure_panel_focus_visible()
            self._note_ui_activity()
            self.update()
        elif c == Command.SELECT_VIDEO_ASPECT:
            self._select_video_aspect(cmd.video_aspect_index)
        elif c == Command.OPEN_SUBTITLE_BROWSE:
            self._open_subtitle_browse()
        elif c == Command.CLOSE_SUBTITLE_BROWSE:
            self._close_subtitle_browse()
        elif c == Command.BROWSE_BACK:
            self._browse_back()
        elif c == Command.MOVE_BROWSE_FOCUS:
            browse_rows = self._state.browse_rows or []
            self._state.browse_focus = max(
                0, min(len(browse_rows) - 1, self._state.browse_focus + cmd.delta)
            )
            self._rebuild_layout()
            self._ensure_panel_focus_visible()
            self._note_ui_activity()
            self.update()
        elif c == Command.ACTIVATE_BROWSE:
            self._activate_browse_row(cmd.browse_index)
            self.update()
        elif c == Command.MOVE_CROSS_FOCUS:
            self._state = move_cross_focus(self._state, cmd.delta)
            self._keyboard_activity()
            self.update()
        elif c == Command.TOGGLE_FOCUS_ZONE:
            if self._state.focus_zone == FocusZone.TIMELINE:
                self._stop_key_scrub()
            self._state = toggle_focus_zone(self._state)
            self._keyboard_activity()
            self.update()
        elif c == Command.ACTIVATE_CROSS:
            self._handle_hit(self._state.cross_focus)
            self._keyboard_activity()
        elif c == Command.MOVE_TRACK_FOCUS:
            self._state = move_track_focus(self._state, cmd.delta)
            self._rebuild_layout()
            self._ensure_panel_focus_visible()
            self._note_ui_activity()
            self.update()
        elif c == Command.MOVE_TRACK_ACTION_FOCUS:
            self._state = move_track_action_focus(self._state, cmd.delta)
            self._note_ui_activity()
            self.update()
        elif c == Command.ACTIVATE_TRACK_ACTION:
            action = self._state.track_action_focus
            if action == "save":
                self._start_napi_save()
            elif action == "delete":
                self._delete_napi_subtitle()
            self._note_ui_activity()
        elif c == Command.ADJUST_SUB_DELAY:
            self._adjust_sub_delay(cmd.delta)
            self._note_ui_activity()
            self.update()
        elif c == Command.SELECT_TRACK:
            self._select_track(cmd.track_index)
        elif c == Command.START_MOUSE_SCRUB:
            if self._state.view == View.WATCHING:
                self.show_scrubber()
            scrub = self._state.ensure_scrub()
            scrub.seek_dragging = True
            self.grabMouse()
            self._hide_timer.stop()
            self._dim_timer.stop()
            if cmd.pos:
                self._seek_at(cmd.pos, immediate=True)
        elif c == Command.MOUSE_SCRUB:
            pass
        elif c == Command.FINISH_MOUSE_SCRUB:
            scrub = self._state.ensure_scrub()
            scrub.seek_dragging = False
            self.releaseMouse()
            self._finish_scrub()
            if self._state.view == View.SCRUB:
                self._dismiss_to_watching()
            else:
                self.show_controls()
        elif c == Command.START_KEY_SCRUB:
            self._sync_playback_to_scrub()
            scrub = self._state.ensure_scrub()
            if scrub.duration <= 0:
                self._controller.seek_relative(cmd.delta * ScrubEngine.INITIAL_KEY_SCRUB_S)
                return
            if self._state.view == View.WATCHING:
                self.show_scrubber()
            self._hide_timer.stop()
            self._dim_timer.stop()
            self._ui_opacity = 1.0
            self._key_scrub_timer.start()
            scrub, seek, debounce = ScrubEngine.start_key_scrub(scrub, cmd.delta)
            self._controller.seek_relative(cmd.delta * ScrubEngine.INITIAL_KEY_SCRUB_S)
            self._apply_scrub_result(scrub, None, debounce)
            self._key_scrub_tick_timer.start()
            self._keyboard_activity()
        elif c == Command.STOP_KEY_SCRUB:
            self._stop_key_scrub()
            if self._state.view == View.SCRUB:
                self._dismiss_to_watching()
            self._keyboard_activity()
        elif c in (Command.TIMELINE_UP, Command.TIMELINE_DOWN):
            self._stop_key_scrub()
            if c == Command.TIMELINE_UP:
                self._state = self._state.__class__(
                    **{**self._state.__dict__, "focus_zone": FocusZone.CONTROLS}
                )
                self.update()
            elif c == Command.TIMELINE_DOWN:
                self._dismiss_to_watching()
            self._keyboard_activity()
        elif c == Command.HIT:
            if cmd.hit_key in CROSS_ORDER:
                self._state.cross_focus = cmd.hit_key
                self._state.focus_zone = FocusZone.CONTROLS
            self._handle_hit(cmd.hit_key)
        elif c == Command.CLICK_OUTSIDE:
            self._dismiss_to_watching()
        elif c == Command.START_VOLUME_ADJUST:
            self._start_volume_adjust(cmd.delta, cmd.volume_step)
        elif c == Command.STOP_VOLUME_ADJUST:
            self._stop_volume_adjust()
        elif c == Command.TOGGLE_MUTE:
            self._controller.toggle_mute()
            self._state.muted = self._controller.is_muted()
            self._flash_volume()
            if self._state.view != View.WATCHING:
                self._keyboard_activity()
            self.update()
        elif c == Command.SEEK_TO_FRACTION:
            self._stop_key_scrub()
            scrub = self._state.ensure_scrub()
            scrub, seek, debounce = ScrubEngine.scrub_to_fraction(
                scrub, cmd.fraction, immediate=True
            )
            self._apply_scrub_result(scrub, seek, debounce)
            if self._state.view != View.WATCHING:
                self._keyboard_activity()
        elif c == Command.KEYBOARD_ACTIVITY:
            self._keyboard_activity()

    def _handle_hit(self, key: str):
        if key == "m1":
            self._controller.seek_relative(-1)
        elif key == "m10":
            self._controller.seek_relative(-10)
        elif key == "center":
            self._controller.toggle_pause()
        elif key == "p10":
            self._controller.seek_relative(10)
        elif key == "p1":
            self._controller.seek_relative(1)
        elif key == "subs":
            self._execute(RoutedCommand(Command.OPEN_TRACKS, track_kind=TrackKind.SUBTITLES))
            return
        elif key == "audio":
            self._execute(RoutedCommand(Command.OPEN_TRACKS, track_kind=TrackKind.AUDIO))
            return
        elif key == "video":
            self._execute(RoutedCommand(Command.OPEN_VIDEO))
            return
        elif key.startswith("video:"):
            self._select_video_aspect(int(key.split(":")[1]))
            return
        elif key.startswith("track:"):
            if key.endswith(":save"):
                self._start_napi_save()
                return
            if key.endswith(":delete"):
                self._delete_napi_subtitle()
                return
            if key.endswith(":delay-earlier"):
                self._adjust_sub_delay(-1)
                return
            if key.endswith(":delay-later"):
                self._adjust_sub_delay(1)
                return
            self._select_track(int(key.split(":")[1]))
            return
        elif key.startswith("browse:"):
            self._activate_browse_row(int(key.split(":")[1]))
            self.update()
            return
        self._sync_playback_to_scrub()
        self.show_controls()

    def _select_video_aspect(self, index: int) -> None:
        if index < 0 or index >= len(VIDEO_ASPECT_MODES):
            return
        self._controller.set_video_aspect_mode(VIDEO_ASPECT_MODES[index])
        self._state.video_focus = index
        self.persist_video_aspect()
        self._note_ui_activity()
        self.update()

    def _select_track(self, index: int):
        rows = self._state.track_rows or []
        if index < 0 or index >= len(rows):
            return
        row = rows[index]
        if self._state.track_kind == TrackKind.SUBTITLES:
            if row.opens_browse:
                self._open_subtitle_browse()
                return
            if row.opens_napi_download:
                self._start_napi_download()
                return
            if row.is_action:
                return
            self._selected_subtitle_path = self._controller.subtitle_share_path(row.mpv_id)
            self._controller.set_sid(row.mpv_id)
        else:
            self._controller.set_aid(row.mpv_id)
        self._refresh_track_rows()
        self._maybe_persist_track_selection()
        self.update()

    def _read_share_file_bytes(self, absolute_path: PurePosixPath) -> bytes | None:
        if self._file_repository is None:
            return None

        def collect(stream) -> bytes:
            return b"".join(stream)

        try:
            return self._file_repository.use_read_file_stream(absolute_path, collect)
        except OSError:
            return None

    def _read_subtitle_uri_for_hash(self, uri: str) -> bytes | None:
        if uri.startswith("file://"):
            path = Path(unquote(urlparse(uri).path))
            try:
                return path.read_bytes()
            except OSError:
                return None
        if self._library_path is None or self._playback_uri_resolver is None:
            return None
        basename = uri.replace("\\", "/").rsplit("/", 1)[-1]
        parent = self._library_path.parent if self._library_path.name else self._library_path
        candidates = {basename}
        if self._library_path is not None:
            candidates.add(subtitle_sidecar_path(self._library_path).name)
        for name in candidates:
            try:
                resolved = self._playback_uri_resolver.resolve_path(share_path(parent / name))
            except OSError:
                continue
            data = self._read_share_file_bytes(resolved)
            if data is not None:
                return data
        return None

    def _find_existing_subtitle_track(self, srt_bytes: bytes | None) -> int | None:
        if srt_bytes is None:
            return None
        return self._controller.find_subtitle_track_for_content(
            srt_bytes,
            read_uri=self._read_subtitle_uri_for_hash,
        )

    def _load_external_subtitle(self, path: PurePosixPath) -> None:
        resolver = self._playback_uri_resolver
        if resolver is None:
            return
        share = share_path(path)
        self._selected_subtitle_path = share
        resolved = None
        srt_bytes = None
        try:
            resolved = self._resolve_subtitle_share_path(share)
            srt_bytes = self._read_share_file_bytes(resolved)
        except OSError:
            pass
        existing = self._find_existing_subtitle_track(srt_bytes)
        if existing is not None:
            self._controller.remember_subtitle_share_path(existing, share)
            self._controller.set_sid(existing)
            self._refresh_track_rows()
            self._maybe_persist_track_selection()
            self.update()
            return
        try:
            if resolved is None:
                resolved = self._resolve_subtitle_share_path(share)
            uri = resolver.stream_uri(resolved)
        except OSError as exc:
            logger.warning("Could not resolve subtitle URI for %s: %s", path, exc)
            return
        track_id = self._controller.add_subtitle(
            uri,
            display_name=share.name,
            share_path=share,
        )
        if track_id is not None:
            if srt_bytes is not None:
                self._controller.remember_subtitle_content_hash(track_id, srt_bytes)
            self._controller.set_sid(track_id)
        self._refresh_track_rows()
        self._maybe_persist_track_selection()
        self.update()

    def _load_cached_napi_subtitle(self, local_path: Path) -> None:
        if self._library_path is not None:
            self._selected_subtitle_path = share_path(subtitle_sidecar_path(self._library_path))
        try:
            srt_bytes = local_path.read_bytes()
        except OSError:
            srt_bytes = None

        if srt_bytes is not None:
            existing = self._find_existing_subtitle_track(srt_bytes)
            if existing is not None:
                self._controller.mark_napi_track(existing)
                self._controller.set_sid(existing)
                self._napi_status_message = None
                self._refresh_track_rows()
                self._maybe_persist_track_selection()
                self.update()
                return

        uri = local_path.resolve().as_uri()
        display_name = (
            subtitle_sidecar_path(self._library_path).name
            if self._library_path is not None
            else local_path.name
        )
        track_id = self._controller.add_subtitle(
            uri,
            display_name=display_name,
            share_path=self._selected_subtitle_path,
        )
        if track_id is not None:
            if srt_bytes is not None:
                self._controller.remember_subtitle_content_hash(track_id, srt_bytes)
            self._controller.mark_napi_track(track_id)
            self._controller.set_sid(track_id)
        self._napi_status_message = None
        self._refresh_track_rows()
        self._maybe_persist_track_selection()
        self.update()

    def _adjust_sub_delay(self, steps: int) -> None:
        if self._controller.current_sid() is None:
            return
        self._controller.adjust_sub_delay(steps=steps)
        self.update()

    def _start_napi_download(self) -> None:
        library_path = self._library_path
        if (
            library_path is None
            or self._napi_downloading
            or self._subtitle_cache is None
            or self._napi_provider is None
            or self._video_reader is None
        ):
            return
        self._napi_downloading = True
        self._napi_status_message = None
        self._refresh_track_rows()
        self.update()
        worker = NapiDownloadWorker(
            library_path,
            video_reader=self._video_reader,
            provider=self._napi_provider,
            subtitle_cache=self._subtitle_cache,
            language=self._napi_language,
            playback_uri_resolver=self._playback_uri_resolver,
            stream_uri=self._stream_uri,
            resolved_video_path=self._resolved_video_path,
            file_repository=self._file_repository,
        )
        worker.signals.finished.connect(
            self._on_napi_download_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.failed.connect(
            self._on_napi_download_failed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._thread_pool.start(worker)

    def _on_napi_download_finished(
        self,
        video_path: PurePosixPath,
        local_path: Path,
        _from_cache: bool,
    ) -> None:
        self._napi_downloading = False
        if self._library_path != video_path:
            return
        self._load_cached_napi_subtitle(local_path)

    def _on_napi_download_failed(self, video_path: PurePosixPath, message: str) -> None:
        self._napi_downloading = False
        if self._library_path != video_path:
            return
        self._napi_status_message = message
        self._refresh_track_rows()
        self.update()

    def _start_napi_save(self, *, overwrite: bool = False) -> None:
        library_path = self._library_path
        if (
            library_path is None
            or self._napi_saving
            or self._subtitle_cache is None
            or self._napi_saved_state is None
            or self._file_writer is None
        ):
            return
        self._napi_saving = True
        worker = NapiSaveWorker(
            library_path,
            subtitle_cache=self._subtitle_cache,
            file_writer=self._file_writer,
            saved_state=self._napi_saved_state,
            overwrite=overwrite,
            playback_uri_resolver=self._playback_uri_resolver,
        )
        worker.signals.finished.connect(
            self._on_napi_save_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.exists.connect(
            self._on_napi_save_exists,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.failed.connect(
            self._on_napi_save_failed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._thread_pool.start(worker)

    def _on_napi_save_finished(self, video_path: PurePosixPath, _sidecar: PurePosixPath) -> None:
        self._napi_saving = False
        if self._library_path != video_path:
            return
        self._napi_status_message = "Saved to NAS"
        self._refresh_track_rows()
        self.update()

    def _on_napi_save_exists(self, video_path: PurePosixPath, sidecar: PurePosixPath) -> None:
        self._napi_saving = False
        if self._library_path != video_path:
            return
        answer = QMessageBox.question(
            self,
            "Replace subtitle?",
            f"{sidecar.name} already exists on the NAS. Replace it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._start_napi_save(overwrite=True)

    def _on_napi_save_failed(self, video_path: PurePosixPath, message: str) -> None:
        self._napi_saving = False
        if self._library_path != video_path:
            return
        self._napi_status_message = message
        self._refresh_track_rows()
        self.update()

    def _delete_napi_subtitle(self) -> None:
        library_path = self._library_path
        if library_path is None or self._subtitle_cache is None:
            return
        if self._napi_saved_state is not None and self._napi_saved_state.is_saved_to_nas(library_path):
            return
        active_sid = self._controller.current_sid()
        napi_ids = list(self._controller.napi_track_ids())
        for track_id in napi_ids:
            self._controller.remove_subtitle(track_id)
        if active_sid is not None and active_sid in napi_ids:
            self._controller.set_sid(None)
            self._selected_subtitle_path = None
        self._subtitle_cache.delete(library_path)
        if self._napi_saved_state is not None:
            self._napi_saved_state.clear(library_path)
        self._napi_status_message = None
        self._refresh_track_rows()
        self._maybe_persist_track_selection()
        self.update()

    def _apply_scrub_result(self, scrub, seek, debounce):
        self._state.scrub = scrub
        self._state.time_pos = scrub.time_pos
        if scrub.duration > 0:
            self._state.duration = scrub.duration
        if seek:
            self._controller.seek_fraction(seek.fraction, exact=seek.exact)
        if debounce:
            self._seek_apply_timer.start(debounce)
        self.update()

    def _seek_at(self, pos: QPoint, *, immediate: bool = False):
        scrub = self._state.ensure_scrub()
        fraction = ScrubEngine.fraction_at(
            pos.x(), self._layout.seek_inner.x(), self._layout.seek_inner.width()
        )
        scrub, seek, debounce = ScrubEngine.scrub_to_fraction(scrub, fraction, immediate=immediate)
        self._apply_scrub_result(scrub, seek, debounce)

    def _finish_scrub(self):
        self._seek_apply_timer.stop()
        scrub = self._state.ensure_scrub()
        scrub, seek = ScrubEngine.finish_scrub(scrub, force=True)
        self._state.scrub = scrub
        self._state.time_pos = scrub.time_pos
        if seek:
            self._controller.seek_fraction(seek.fraction, exact=seek.exact)
        QTimer.singleShot(200, self._sync_playback_to_scrub)
        self.update()

    def _apply_pending_seek(self):
        scrub = self._state.ensure_scrub()
        scrub, seek = ScrubEngine.apply_pending(scrub)
        self._state.scrub = scrub
        if seek:
            scrub.key_scrub_dirty = True
            self._controller.seek_fraction(seek.fraction, exact=seek.exact)

    def _stop_key_scrub(self, *, finalize: bool = True):
        self._key_scrub_tick_timer.stop()
        scrub = self._state.ensure_scrub()
        held = self._key_scrub_timer.isValid() and self._key_scrub_timer.elapsed() > 80
        scrub, seek = ScrubEngine.stop_key_scrub(scrub, finalize=finalize and held)
        self._state.scrub = scrub
        if seek:
            self._controller.seek_fraction(seek.fraction, exact=seek.exact)
            self._state.time_pos = scrub.time_pos
        self.update()

    def _apply_volume_delta(self, delta: float) -> None:
        self._controller.change_volume(delta)
        self._state.volume = self._controller.volume()
        self._flash_volume()
        if self._state.view != View.WATCHING:
            self._keyboard_activity()
        self.update()

    def _start_volume_adjust(self, direction: int, step_base: int) -> None:
        self._volume_adjust_direction = direction
        self._volume_step_base = step_base
        self._volume_adjust_timer.start()
        self._apply_volume_delta(direction * step_base)
        self._volume_adjust_tick_timer.start()

    def _stop_volume_adjust(self) -> None:
        self._volume_adjust_tick_timer.stop()
        self._volume_adjust_direction = 0

    def _on_volume_adjust_tick(self) -> None:
        if self._volume_adjust_direction == 0:
            return
        step = VolumeEngine.step(
            self._volume_adjust_timer.elapsed(),
            step_base=self._volume_step_base,
        )
        self._apply_volume_delta(self._volume_adjust_direction * step)

    def _on_key_scrub_tick(self):
        scrub = self._state.ensure_scrub()
        scrub.key_scrub_elapsed_ms = self._key_scrub_timer.elapsed()
        scrub, seek, debounce = ScrubEngine.key_scrub_tick(scrub)
        self._apply_scrub_result(scrub, seek, debounce)

    def keyPressEvent(self, event):
        if routed := self._router.route_key(
            event, self._state, has_media=self._controller.has_media()
        ):
            if not event.isAutoRepeat():
                if key := self._press_key_for_command(routed):
                    self._begin_press(key)
            self._execute(routed)
            if routed.command != Command.SHOW_CONTROLS or self._state.view != View.WATCHING:
                event.accept()
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        self._end_press()
        if routed := self._router.route_key_release(event, self._state):
            self._execute(routed)
            event.accept()
            return
        super().keyReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._state.view in (View.TRACKS, View.VIDEO, View.SUBTITLE_BROWSE):
            delta = event.angleDelta().y()
            if delta != 0:
                self._scroll_panel_by(delta)
                event.accept()
                return
        super().wheelEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        scrub = self._state.scrub
        if scrub and scrub.seek_dragging:
            self._seek_at(event.position().toPoint())
            return
        if self._tracks_inactivity():
            self._note_ui_activity()
        if routed := self._router.route_mouse_move(self._state, scrubbing=False):
            if routed.command == Command.SHOW_CONTROLS:
                self.show_controls()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._end_press()
        scrub = self._state.scrub
        if routed := self._router.route_mouse_release(
            event, scrubbing=bool(scrub and scrub.seek_dragging)
        ):
            self._execute(routed)
            return
        self.update()
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if self._state.view in (View.CONTROLS, View.TRACKS, View.VIDEO, View.SCRUB, View.SUBTITLE_BROWSE):
            self._rebuild_layout()
        routed = self._router.route_mouse_press(
            event,
            self._state,
            self._layout.hit_regions,
            has_media=self._controller.has_media(),
            in_controls_area=lambda pos: any(
                r.contains(pos) for r in self._layout.hit_regions.values()
            ),
        )
        if routed:
            if key := self._press_key_for_command(routed):
                self._begin_press(key)
            self._execute(routed)
            return
        super().mousePressEvent(event)

    def paintEvent(self, _event: QPaintEvent):
        w, h = self.width(), self.height()
        if not self._controller.has_media():
            self._after_paint_anim()
            return

        if self._state.view == View.WATCHING:
            if self._state.volume_flash:
                painter = QPainter(self)
                if painter.isActive():
                    try:
                        painter.save()
                        painter.setOpacity(self._ui_opacity)
                        paint_volume(painter, w, h, self._state.volume, muted=self._state.muted)
                        painter.restore()
                    finally:
                        painter.end()
            self._after_paint_anim()
            return

        self._rebuild_layout()
        press_key, press_strength_val = self._press_state()
        painter = QPainter(self)
        if not painter.isActive():
            return
        try:
            painter.save()
            painter.setOpacity(self._ui_opacity)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            if self._state.view == View.CONTROLS:
                paint_cross_controls(
                    painter,
                    self._state,
                    self._layout,
                    playing=self._controller.is_playing(),
                    press_key=press_key,
                    press_strength=press_strength_val,
                )
                paint_corner_hints(
                    painter,
                    self._layout,
                    subtitle_name=self._controller.current_subtitle_label(),
                    audio_name=self._controller.current_audio_label(),
                    video_name=video_aspect_label(self._controller.video_aspect_mode()),
                )
                if self._state.volume_flash:
                    paint_volume(painter, w, h, self._state.volume, muted=self._state.muted)
            elif self._state.view == View.SCRUB:
                paint_timeline(
                    painter,
                    self._state,
                    self._layout,
                    timeline_focused=True,
                )
            elif self._state.view == View.TRACKS:
                painter.fillRect(self.rect(), QColor.fromRgbF(0, 0, 0, 0.42))
                paint_track_sheet(
                    painter,
                    w,
                    h,
                    self._state,
                    self._layout,
                    sid=self._controller.current_sid(),
                    aid=self._controller.current_aid(),
                    sub_delay=self._controller.sub_delay(),
                    press_key=press_key,
                    press_strength=press_strength_val,
                )
            elif self._state.view == View.VIDEO:
                painter.fillRect(self.rect(), QColor.fromRgbF(0, 0, 0, 0.42))
                paint_video_sheet(
                    painter,
                    w,
                    h,
                    self._state,
                    self._layout,
                    current_mode_index=self._controller.video_aspect_mode_index(),
                    press_key=press_key,
                    press_strength=press_strength_val,
                )
            elif self._state.view == View.SUBTITLE_BROWSE:
                painter.fillRect(self.rect(), QColor.fromRgbF(0, 0, 0, 0.42))
                paint_browse_sheet(
                    painter,
                    w,
                    h,
                    self._state,
                    self._layout,
                    press_key=press_key,
                    press_strength=press_strength_val,
                )
        finally:
            painter.restore()
            painter.end()

        self._after_paint_anim()

    def _after_paint_anim(self) -> None:
        self._sync_press_anim_clock()
        if self._press_anim is not None and not self._press_anim_timer.isActive():
            self._press_anim_timer.start()
