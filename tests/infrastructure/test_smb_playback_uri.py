"""SmbPlaybackUriResolver builds localhost stream URIs."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import PurePosixPath
from unittest.mock import MagicMock, patch

from lumi.infrastructure.smb.smb_playback_uri import SmbPlaybackUriResolver
from lumi.infrastructure.smb.smb_stream_server import SmbHttpStreamServer


def test_playback_uri_streams_via_localhost_http() -> None:
    repo = MagicMock()
    server = SmbHttpStreamServer(repo)
    resolver = SmbPlaybackUriResolver(repo, server, MOCK_LIBRARY_ROOT, {"mp4"})
    try:
        with patch(
            "lumi.infrastructure.smb.smb_playback_uri.resolve_playback_file",
            return_value=MOCK_LIBRARY_ROOT / "Alien/Alien.mkv",
        ):
            repo.file_size.return_value = 999
            uri = resolver.playback_uri(MOCK_LIBRARY_ROOT / "Alien/Alien.mkv")
        assert uri.startswith("http://127.0.0.1:")
        assert "/stream/" in uri
    finally:
        server.shutdown()
