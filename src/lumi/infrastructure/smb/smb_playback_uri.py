"""SMB playback URI resolver — localhost HTTP stream, never copies video files."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.infrastructure.smb.playback_paths import playback_path_candidates, resolve_playback_file, resolve_share_file
from lumi.infrastructure.smb.smb_file_repository import SmbFileRepository
from lumi.infrastructure.smb.smb_stream_server import SmbHttpStreamServer


class SmbPlaybackUriResolver:
    def __init__(
        self,
        smb_file_repository: SmbFileRepository,
        stream_server: SmbHttpStreamServer,
        library_root: PurePosixPath,
        video_extensions: set[str],
    ) -> None:
        self._smb_file_repository = smb_file_repository
        self._stream_server = stream_server
        self._library_root = library_root
        self._video_extensions = video_extensions

    def playback_uri(self, absolute_path: PurePosixPath) -> str:
        self._smb_file_repository.reconnect_for_playback()
        resolved = resolve_playback_file(
            self._smb_file_repository,
            absolute_path,
            self._library_root,
            self._video_extensions,
        )
        return self.stream_uri(resolved)

    def resolve_path(self, hint_path: PurePosixPath) -> PurePosixPath:
        self._smb_file_repository.reconnect_for_playback()
        return resolve_playback_file(
            self._smb_file_repository,
            hint_path,
            self._library_root,
            self._video_extensions,
        )

    def resolve_share_file(self, hint_path: PurePosixPath) -> PurePosixPath:
        return resolve_share_file(
            self._smb_file_repository,
            hint_path,
            self._library_root,
        )

    def stream_uri(self, absolute_path: PurePosixPath) -> str:
        for candidate in playback_path_candidates(absolute_path, self._library_root):
            if self._smb_file_repository.file_size(candidate) is not None:
                return self._stream_server.resolve_stream_uri(candidate)
        raise FileNotFoundError(f"SMB file not found: {absolute_path}")

    def shutdown(self) -> None:
        self._stream_server.shutdown()
