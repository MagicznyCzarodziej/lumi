from __future__ import annotations

from pathlib import Path, PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from lumi.ui.workers.napi_download_worker import NapiDownloadWorker
from lumi.ui.player.overlay.services.base import OverlayService
from lumi.ui.workers.napi_save_worker import NapiSaveWorker


class NapiService(OverlayService):
    def start_download(self) -> None:
        library_path = self._rt.library_path
        if (
            library_path is None
            or self._rt.napi_downloading
            or self._rt.deps.subtitle_cache is None
            or self._rt.deps.napi_provider is None
            or self._rt.deps.video_reader is None
        ):
            return
        self._rt.napi_downloading = True
        self._rt.napi_status_message = None
        self._o.tracks.refresh_rows()
        self._update()
        worker = NapiDownloadWorker(
            library_path,
            video_reader=self._rt.deps.video_reader,
            provider=self._rt.deps.napi_provider,
            subtitle_cache=self._rt.deps.subtitle_cache,
            language=self._rt.deps.napi_language,
            playback_uri_resolver=self._rt.deps.playback_uri_resolver,
            stream_uri=self._rt.stream_uri,
            resolved_video_path=self._rt.resolved_video_path,
            file_repository=self._rt.deps.file_repository,
        )
        worker.signals.finished.connect(
            self._o._worker_slots.napi_download_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.failed.connect(
            self._o._worker_slots.napi_download_failed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._rt.thread_pool.start(worker)

    def on_download_finished(
        self,
        video_path: PurePosixPath,
        local_path: Path,
        _from_cache: bool,
    ) -> None:
        self._rt.napi_downloading = False
        if self._rt.library_path != video_path:
            return
        self._o.subtitles.load_cached_napi(local_path)

    def on_download_failed(self, video_path: PurePosixPath, message: str) -> None:
        self._rt.napi_downloading = False
        if self._rt.library_path != video_path:
            return
        self._rt.napi_status_message = message
        self._o.tracks.refresh_rows()
        self._update()

    def start_save(self, *, overwrite: bool = False) -> None:
        library_path = self._rt.library_path
        if (
            library_path is None
            or self._rt.napi_saving
            or self._rt.deps.subtitle_cache is None
            or self._rt.deps.napi_saved_state is None
            or self._rt.deps.file_writer is None
        ):
            return
        self._rt.napi_saving = True
        worker = NapiSaveWorker(
            library_path,
            subtitle_cache=self._rt.deps.subtitle_cache,
            file_writer=self._rt.deps.file_writer,
            saved_state=self._rt.deps.napi_saved_state,
            overwrite=overwrite,
            playback_uri_resolver=self._rt.deps.playback_uri_resolver,
        )
        worker.signals.finished.connect(
            self._o._worker_slots.napi_save_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.exists.connect(
            self._o._worker_slots.napi_save_exists,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.signals.failed.connect(
            self._o._worker_slots.napi_save_failed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._rt.thread_pool.start(worker)

    def on_save_finished(self, video_path: PurePosixPath, _sidecar: PurePosixPath) -> None:
        self._rt.napi_saving = False
        if self._rt.library_path != video_path:
            return
        self._rt.napi_status_message = "Saved to NAS"
        self._o.tracks.refresh_rows()
        self._update()

    def on_save_exists(self, video_path: PurePosixPath, sidecar: PurePosixPath) -> None:
        self._rt.napi_saving = False
        if self._rt.library_path != video_path:
            return
        answer = QMessageBox.question(
            self._o,
            "Replace subtitle?",
            f"{sidecar.name} already exists on the NAS. Replace it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._o.napi.start_save(overwrite=True)

    def on_save_failed(self, video_path: PurePosixPath, message: str) -> None:
        self._rt.napi_saving = False
        if self._rt.library_path != video_path:
            return
        self._rt.napi_status_message = message
        self._o.tracks.refresh_rows()
        self._update()

    def delete_subtitle(self) -> None:
        library_path = self._rt.library_path
        if library_path is None or self._rt.deps.subtitle_cache is None:
            return
        if self._rt.deps.napi_saved_state is not None and self._rt.deps.napi_saved_state.is_saved_to_nas(library_path):
            return
        active_sid = self._rt.controller.current_sid()
        napi_ids = list(self._rt.controller.napi_track_ids())
        for track_id in napi_ids:
            self._rt.controller.remove_subtitle(track_id)
        if active_sid is not None and active_sid in napi_ids:
            self._rt.controller.set_sid(None)
            self._rt.selected_subtitle_path = None
        self._rt.deps.subtitle_cache.delete(library_path)
        if self._rt.deps.napi_saved_state is not None:
            self._rt.deps.napi_saved_state.clear(library_path)
        self._rt.napi_status_message = None
        self._o.tracks.refresh_rows()
        self._o.tracks.maybe_persist_selection()
        self._update()
