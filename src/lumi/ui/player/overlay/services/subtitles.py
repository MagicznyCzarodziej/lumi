from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

from lumi.domain.subtitles.sidecar_path import subtitle_sidecar_path
from lumi.domain.subtitles.browse import share_path

from lumi.ui.player.overlay.services.base import OverlayService

logger = logging.getLogger(__name__)


class SubtitleService(OverlayService):
    def read_share_file_bytes(self, absolute_path: PurePosixPath) -> bytes | None:
        if self._rt.deps.file_repository is None:
            return None

        def collect(stream) -> bytes:
            return b"".join(stream)

        try:
            return self._rt.deps.file_repository.use_read_file_stream(absolute_path, collect)
        except OSError:
            return None

    def _read_subtitle_uri_for_hash(self, uri: str) -> bytes | None:
        if uri.startswith("file://"):
            path = Path(unquote(urlparse(uri).path))
            try:
                return path.read_bytes()
            except OSError:
                return None
        if self._rt.library_path is None or self._rt.deps.playback_uri_resolver is None:
            return None
        basename = uri.replace("\\", "/").rsplit("/", 1)[-1]
        parent = self._rt.library_path.parent if self._rt.library_path.name else self._rt.library_path
        candidates = {basename}
        if self._rt.library_path is not None:
            candidates.add(subtitle_sidecar_path(self._rt.library_path).name)
        for name in candidates:
            try:
                resolved = self._rt.deps.playback_uri_resolver.resolve_path(share_path(parent / name))
            except OSError:
                continue
            data = self._o.subtitles.read_share_file_bytes(resolved)
            if data is not None:
                return data
        return None

    def _find_existing_subtitle_track(self, srt_bytes: bytes | None) -> int | None:
        if srt_bytes is None:
            return None
        return self._rt.controller.find_subtitle_track_for_content(
            srt_bytes,
            read_uri=self._read_subtitle_uri_for_hash,
        )

    def load_external(self, path: PurePosixPath) -> None:
        resolver = self._rt.deps.playback_uri_resolver
        if resolver is None:
            return
        share = share_path(path)
        self._rt.selected_subtitle_path = share
        resolved = None
        srt_bytes = None
        try:
            resolved = self._o.tracks.resolve_subtitle_share_path(share)
            srt_bytes = self._o.subtitles.read_share_file_bytes(resolved)
        except OSError:
            pass
        existing = self._find_existing_subtitle_track(srt_bytes)
        if existing is not None:
            self._rt.controller.remember_subtitle_share_path(existing, share)
            self._rt.controller.set_sid(existing)
            self._o.tracks.refresh_rows()
            self._o.tracks.maybe_persist_selection()
            self._update()
            return
        try:
            if resolved is None:
                resolved = self._o.tracks.resolve_subtitle_share_path(share)
            uri = resolver.stream_uri(resolved)
        except OSError as exc:
            logger.warning("Could not resolve subtitle URI for %s: %s", path, exc)
            return
        track_id = self._rt.controller.add_subtitle(
            uri,
            display_name=share.name,
            share_path=share,
        )
        if track_id is not None:
            if srt_bytes is not None:
                self._rt.controller.remember_subtitle_content_hash(track_id, srt_bytes)
            self._rt.controller.set_sid(track_id)
        self._o.tracks.refresh_rows()
        self._o.tracks.maybe_persist_selection()
        self._update()

    def load_cached_napi(self, local_path: Path) -> None:
        if self._rt.library_path is not None:
            self._rt.selected_subtitle_path = share_path(subtitle_sidecar_path(self._rt.library_path))
        try:
            srt_bytes = local_path.read_bytes()
        except OSError:
            srt_bytes = None

        if srt_bytes is not None:
            existing = self._find_existing_subtitle_track(srt_bytes)
            if existing is not None:
                self._rt.controller.mark_napi_track(existing)
                self._rt.controller.set_sid(existing)
                self._rt.napi_status_message = None
                self._o.tracks.refresh_rows()
                self._o.tracks.maybe_persist_selection()
                self._update()
                return

        uri = local_path.resolve().as_uri()
        display_name = (
            subtitle_sidecar_path(self._rt.library_path).name
            if self._rt.library_path is not None
            else local_path.name
        )
        track_id = self._rt.controller.add_subtitle(
            uri,
            display_name=display_name,
            share_path=self._rt.selected_subtitle_path,
        )
        if track_id is not None:
            if srt_bytes is not None:
                self._rt.controller.remember_subtitle_content_hash(track_id, srt_bytes)
            self._rt.controller.mark_napi_track(track_id)
            self._rt.controller.set_sid(track_id)
        self._rt.napi_status_message = None
        self._o.tracks.refresh_rows()
        self._o.tracks.maybe_persist_selection()
        self._update()

    def adjust_delay(self, steps: int) -> None:
        if self._rt.controller.current_sid() is None:
            return
        self._rt.controller.adjust_sub_delay(steps=steps)
        self._update()
