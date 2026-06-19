"""SMB playback URI resolver — localhost HTTP stream, never copies video files."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.infrastructure.smb.playback_paths import resolve_playback_file
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
        resolved = resolve_playback_file(
            self._smb_file_repository,
            absolute_path,
            self._library_root,
            self._video_extensions,
        )
        return self._stream_server.resolve_stream_uri(resolved)

    def shutdown(self) -> None:
        self._stream_server.shutdown()
